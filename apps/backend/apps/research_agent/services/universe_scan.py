from __future__ import annotations

from collections import Counter

from django.db import transaction
from django.utils import timezone

from apps.agents.models import AgentPipelineType, AgentStatus
from apps.agents.services.orchestrator import run_agent_pipeline
from apps.research_agent.models import (
    MarketTriageDecision,
    MarketUniverseScanRun,
    MarketUniverseScanRunStatus,
    PursuitCandidate,
    TriageStatus,
)
from apps.research_agent.services.market_triage import TriageInput, build_market_queryset, evaluate_market, resolve_profile


@transaction.atomic
def run_universe_scan(
    *,
    filter_profile: str | None = None,
    provider_scope: list[str] | None = None,
    source_scope: list[str] | None = None,
    triggered_by: str = 'manual',
) -> MarketUniverseScanRun:
    profile_slug, triage_profile = resolve_profile(filter_profile)
    now = timezone.now()

    run = MarketUniverseScanRun.objects.create(
        status=MarketUniverseScanRunStatus.RUNNING,
        triggered_by=triggered_by,
        filter_profile=profile_slug,
        provider_scope=provider_scope or [],
        source_scope=source_scope or [],
        started_at=now,
        details={'profile': profile_slug},
    )

    market_outcomes: list[tuple] = []
    reasons = Counter()
    flags = Counter()

    markets = list(build_market_queryset(provider_scope=provider_scope, source_scope=source_scope))
    for market in markets:
        outcome = evaluate_market(TriageInput(market=market, profile=triage_profile, now=now))
        reasons.update(outcome.exclusion_reasons)
        flags.update(outcome.flags)
        market_outcomes.append((market, outcome))

    decisions = [
        MarketTriageDecision(
            run=run,
            market=market,
            triage_status=outcome.triage_status,
            triage_score=outcome.triage_score,
            exclusion_reasons=outcome.exclusion_reasons,
            flags=outcome.flags,
            narrative_coverage=outcome.narrative_coverage,
            narrative_relevance=outcome.narrative_relevance,
            narrative_confidence=outcome.narrative_confidence,
            source_mix=outcome.source_mix,
            rationale=outcome.rationale,
            details=outcome.details,
        )
        for market, outcome in market_outcomes
    ]
    created_decisions = MarketTriageDecision.objects.bulk_create(decisions)

    decision_map = {decision.market_id: decision for decision in created_decisions}
    pursuits = []
    for market, outcome in market_outcomes:
        decision = decision_map[market.id]
        if decision.triage_status in {TriageStatus.SHORTLISTED, TriageStatus.WATCH}:
            pursuits.append(
                PursuitCandidate(
                    run=run,
                    triage_decision=decision,
                    market=market,
                    provider_slug=market.provider.slug,
                    liquidity=market.liquidity,
                    volume_24h=market.volume_24h,
                    time_to_resolution_hours=outcome.time_to_resolution_hours,
                    market_probability=market.current_market_probability,
                    narrative_coverage=decision.narrative_coverage,
                    narrative_direction=outcome.narrative_direction,
                    source_mix=decision.source_mix,
                    triage_score=decision.triage_score,
                    triage_status=decision.triage_status,
                    rationale=decision.rationale,
                    details={'flags': decision.flags, 'exclusion_reasons': decision.exclusion_reasons},
                )
            )

    PursuitCandidate.objects.bulk_create(pursuits)

    shortlisted = sum(1 for decision in created_decisions if decision.triage_status == TriageStatus.SHORTLISTED)
    watchlist = sum(1 for decision in created_decisions if decision.triage_status == TriageStatus.WATCH)
    filtered = sum(1 for decision in created_decisions if decision.triage_status == TriageStatus.FILTERED_OUT)
    status = MarketUniverseScanRunStatus.SUCCESS if created_decisions else MarketUniverseScanRunStatus.PARTIAL

    run.status = status
    run.finished_at = timezone.now()
    run.markets_considered = len(created_decisions)
    run.markets_filtered_out = filtered
    run.markets_shortlisted = shortlisted
    run.markets_watchlist = watchlist
    run.summary = f'Universe scan completed: {shortlisted} shortlisted, {watchlist} watch, {filtered} filtered.'
    run.details = {
        'profile': profile_slug,
        'top_exclusion_reasons': reasons.most_common(6),
        'top_flags': flags.most_common(8),
    }
    run.save(
        update_fields=[
            'status',
            'finished_at',
            'markets_considered',
            'markets_filtered_out',
            'markets_shortlisted',
            'markets_watchlist',
            'summary',
            'details',
            'updated_at',
        ]
    )
    return run


def run_triage_to_prediction(*, run: MarketUniverseScanRun, limit: int = 10) -> dict:
    shortlist_ids = list(
        run.pursuit_candidates.filter(triage_status=TriageStatus.SHORTLISTED).values_list('market_id', flat=True)[:limit]
    )
    pipeline_run = run_agent_pipeline(
        pipeline_type=AgentPipelineType.RESEARCH_TO_PREDICTION,
        payload={'run_scan': False, 'candidate_limit': max(len(shortlist_ids), 1)},
    )
    return {
        'scan_run_id': run.id,
        'shortlist_market_ids': shortlist_ids,
        'pipeline_run_id': pipeline_run.id,
        'pipeline_status': pipeline_run.status,
        'pipeline_summary': pipeline_run.summary,
        'agent_pipeline_type': AgentPipelineType.RESEARCH_TO_PREDICTION,
        'accepted': pipeline_run.status in {AgentStatus.SUCCESS, AgentStatus.PARTIAL},
    }

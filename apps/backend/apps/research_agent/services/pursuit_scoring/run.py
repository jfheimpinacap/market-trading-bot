from __future__ import annotations

from collections import Counter

from django.db import transaction
from django.utils import timezone

from apps.research_agent.models import (
    MarketResearchCandidate,
    PredictionHandoffCandidate,
    ResearchHandoffPriority,
    ResearchPursuitRecommendation,
    ResearchPursuitRun,
    ResearchPursuitScore,
    ResearchStructuralAssessment,
)
from apps.research_agent.services.pursuit_scoring.prediction_handoff import build_prediction_handoff
from apps.research_agent.services.pursuit_scoring.pursuit_score import compute_pursuit_score
from apps.research_agent.services.pursuit_scoring.recommendation import recommendation_for_handoff
from apps.research_agent.services.pursuit_scoring.structural_assessment import assess_market_structure


def _candidate_markets(limit: int):
    handoffs = list(
        ResearchHandoffPriority.objects.select_related('linked_market', 'linked_consensus_record', 'linked_divergence_record')
        .filter(linked_market__isnull=False)
        .order_by('-priority_score', '-created_at', '-id')[:limit]
    )
    pairs = [(handoff.linked_market, handoff) for handoff in handoffs]
    seen = {handoff.linked_market_id for handoff in handoffs}
    if len(seen) < limit:
        fallback = MarketResearchCandidate.objects.select_related('linked_market').order_by('-pursue_worthiness_score', '-created_at')[: limit * 2]
        for candidate in fallback:
            if candidate.linked_market_id in seen:
                continue
            pairs.append((candidate.linked_market, None))
            seen.add(candidate.linked_market_id)
            if len(seen) >= limit:
                break
    return pairs


@transaction.atomic
def run_pursuit_review(*, market_limit: int = 120, triggered_by: str = 'manual_api') -> ResearchPursuitRun:
    started_at = timezone.now()
    run = ResearchPursuitRun.objects.create(started_at=started_at, metadata={'triggered_by': triggered_by, 'market_limit': market_limit})

    candidate_handoffs = _candidate_markets(limit=market_limit)
    status_counter: Counter[str] = Counter()
    rec_counter: Counter[str] = Counter()

    for market, handoff in candidate_handoffs:

        structural = assess_market_structure(market=market, now=started_at)
        assessment = ResearchStructuralAssessment.objects.create(
            pursuit_run=run,
            linked_market=market,
            linked_handoff_priority=handoff,
            linked_consensus_record=getattr(handoff, 'linked_consensus_record', None),
            linked_divergence_record=getattr(handoff, 'linked_divergence_record', None),
            liquidity_state=structural.liquidity_state,
            volume_state=structural.volume_state,
            time_to_resolution_state=structural.time_to_resolution_state,
            market_activity_state=structural.market_activity_state,
            structural_status=structural.structural_status,
            assessment_summary=structural.summary,
            reason_codes=structural.reason_codes,
            metadata=structural.metadata,
        )

        pursuit_score, priority_bucket, score_status, score_components, score_summary = compute_pursuit_score(
            assessment=assessment,
            handoff_priority=handoff,
        )
        score = ResearchPursuitScore.objects.create(
            pursuit_run=run,
            linked_assessment=assessment,
            linked_market=market,
            pursuit_score=pursuit_score,
            priority_bucket=priority_bucket,
            score_components=score_components,
            score_status=score_status,
            score_summary=score_summary,
            metadata={'handoff_priority_id': getattr(handoff, 'id', None)},
        )

        handoff_status, handoff_confidence, handoff_reason_codes, handoff_summary = build_prediction_handoff(assessment=assessment, score=score)
        handoff_candidate = PredictionHandoffCandidate.objects.create(
            pursuit_run=run,
            linked_market=market,
            linked_pursuit_score=score,
            linked_assessment=assessment,
            linked_consensus_record=assessment.linked_consensus_record,
            linked_divergence_record=assessment.linked_divergence_record,
            handoff_status=handoff_status,
            handoff_confidence=handoff_confidence,
            handoff_summary=handoff_summary,
            handoff_reason_codes=handoff_reason_codes,
            metadata={'priority_bucket': priority_bucket},
        )
        status_counter[handoff_status] += 1

        rec_type, rationale, reason_codes, blockers, confidence = recommendation_for_handoff(assessment=assessment, handoff=handoff_candidate)
        ResearchPursuitRecommendation.objects.create(
            pursuit_run=run,
            recommendation_type=rec_type,
            target_market=market,
            target_assessment=assessment,
            target_handoff=handoff_candidate,
            rationale=rationale,
            reason_codes=reason_codes,
            confidence=confidence,
            blockers=blockers,
            metadata={'score_status': score_status},
        )
        rec_counter[rec_type] += 1

    run.completed_at = timezone.now()
    run.considered_market_count = run.assessments.count()
    run.considered_handoff_count = run.assessments.exclude(linked_handoff_priority__isnull=True).count()
    run.prediction_ready_count = status_counter['ready']
    run.research_watchlist_count = status_counter['watch']
    run.blocked_count = status_counter['blocked']
    run.deferred_count = status_counter['deferred']
    run.recommendation_summary = dict(rec_counter)
    run.metadata = {**(run.metadata or {}), 'status_summary': dict(status_counter)}
    run.save()
    return run


def get_latest_pursuit_summary():
    run = ResearchPursuitRun.objects.order_by('-started_at', '-id').first()
    if not run:
        return {
            'latest_run': None,
            'totals': {
                'markets_considered': 0,
                'prediction_ready': 0,
                'watchlist': 0,
                'deferred': 0,
                'blocked': 0,
                'high_priority_divergence': 0,
            },
            'recommendation_summary': {},
        }

    high_divergence = run.assessments.filter(linked_divergence_record__divergence_state='high_divergence').count()
    return {
        'latest_run': {
            'id': run.id,
            'started_at': run.started_at,
            'completed_at': run.completed_at,
        },
        'totals': {
            'markets_considered': run.considered_market_count,
            'prediction_ready': run.prediction_ready_count,
            'watchlist': run.research_watchlist_count,
            'deferred': run.deferred_count,
            'blocked': run.blocked_count,
            'high_priority_divergence': high_divergence,
        },
        'recommendation_summary': run.recommendation_summary,
    }

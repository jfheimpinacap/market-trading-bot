from __future__ import annotations

from collections import Counter
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from apps.memory_retrieval.models import MemoryQueryType
from apps.memory_retrieval.services import run_assist
from apps.research_agent.models import (
    MarketResearchCandidate,
    MarketResearchCandidateStatus,
    MarketResearchRecommendation,
    MarketTriageDecisionV2,
    MarketUniverseRun,
    NarrativeCluster,
    NarrativeClusterStatus,
    NarrativeSentiment,
    NarrativeSignal,
    NarrativeSignalStatus,
    ScanRecommendation,
    SourceScanRun,
)
from apps.research_agent.services.clustering import cluster_narratives
from apps.research_agent.services.dedup import deduplicate_narratives
from apps.research_agent.services.demo_fallback import (
    build_demo_narrative_fallback_items,
    is_local_demo_environment,
    is_scan_demo_fallback_enabled,
)
from apps.research_agent.services.filtering import evaluate_structural_filters
from apps.research_agent.services.market_context import infer_target_market, narrative_market_divergence
from apps.research_agent.services.narrative_linking import link_narrative_signals
from apps.research_agent.services.recommendation import decision_for_candidate, recommend_for_signal
from apps.research_agent.services.scoring import compute_pursue_worthiness, score_cluster
from apps.research_agent.services.source_fetch import fetch_parallel_source_items
from apps.research_agent.services.universe_fetch import fetch_market_universe

SCAN_REASON_NO_RSS_SOURCE_CONFIGURED = 'NO_RSS_SOURCE_CONFIGURED'
SCAN_REASON_NO_REDDIT_SOURCE_CONFIGURED = 'NO_REDDIT_SOURCE_CONFIGURED'
SCAN_REASON_NO_X_SOURCE_CONFIGURED = 'NO_X_SOURCE_CONFIGURED'
SCAN_REASON_ALL_SOURCES_EMPTY = 'ALL_SOURCES_EMPTY'
SCAN_REASON_DEMO_MODE_NO_NARRATIVE_FIXTURES = 'DEMO_MODE_NO_NARRATIVE_FIXTURES'
SCAN_REASON_DEMO_FALLBACK_USED = 'DEMO_FALLBACK_USED'
SCAN_REASON_DEMO_FALLBACK_DISABLED = 'DEMO_FALLBACK_DISABLED'


def _cluster_status(*, source_types: set[str], item_count: int, last_seen_at):
    if timezone.now() - last_seen_at > timedelta(days=2):
        return NarrativeClusterStatus.STALE
    if item_count >= 4 and len(source_types) >= 2:
        return NarrativeClusterStatus.CONFIRMED_MULTI_SOURCE
    if item_count <= 1:
        return NarrativeClusterStatus.NOISY
    return NarrativeClusterStatus.EMERGING


def _signal_status(total: Decimal, direction: str, divergence: Decimal) -> str:
    if total >= Decimal('0.7800') and direction in {'bullish_yes', 'bearish_yes'} and divergence >= Decimal('0.2500'):
        return NarrativeSignalStatus.SHORTLISTED
    if total < Decimal('0.4200'):
        return NarrativeSignalStatus.IGNORE
    if direction in {'mixed', 'unclear'}:
        return NarrativeSignalStatus.WATCH
    return NarrativeSignalStatus.CANDIDATE


def _source_type_flags(*, source_ids: list[int] | None = None) -> dict[str, bool]:
    from apps.research_agent.models import NarrativeSource, NarrativeSourceType

    queryset = NarrativeSource.objects.filter(is_enabled=True)
    if source_ids:
        queryset = queryset.filter(id__in=source_ids)
    source_types = set(queryset.values_list('source_type', flat=True))
    return {
        'rss_enabled': NarrativeSourceType.RSS in source_types,
        'reddit_enabled': NarrativeSourceType.REDDIT in source_types,
        'x_enabled': NarrativeSourceType.TWITTER in source_types,
    }


def _base_diagnostics(*, source_ids: list[int] | None = None) -> dict:
    flags = _source_type_flags(source_ids=source_ids)
    return {
        'source_mode': 'local_demo' if is_local_demo_environment() else 'standard',
        **flags,
        'rss_fetch_attempted': flags['rss_enabled'],
        'reddit_fetch_attempted': flags['reddit_enabled'],
        'x_fetch_attempted': flags['x_enabled'],
        'zero_signal_reason_codes': [],
        'diagnostic_summary': '',
    }


def _finalize_diagnostics(*, diagnostics: dict, source_counts: dict[str, int], signal_count: int) -> None:
    reasons: list[str] = []
    if not diagnostics.get('rss_enabled'):
        reasons.append(SCAN_REASON_NO_RSS_SOURCE_CONFIGURED)
    if not diagnostics.get('reddit_enabled'):
        reasons.append(SCAN_REASON_NO_REDDIT_SOURCE_CONFIGURED)
    if not diagnostics.get('x_enabled'):
        reasons.append(SCAN_REASON_NO_X_SOURCE_CONFIGURED)

    real_item_total = int(source_counts.get('rss_count') or 0) + int(source_counts.get('reddit_count') or 0) + int(source_counts.get('x_count') or 0)
    if real_item_total == 0 and signal_count == 0:
        reasons.append(SCAN_REASON_ALL_SOURCES_EMPTY)

    reasons.extend(diagnostics.get('zero_signal_reason_codes') or [])
    diagnostics['zero_signal_reason_codes'] = list(dict.fromkeys(reasons))

    if signal_count > 0:
        diagnostics['diagnostic_summary'] = (
            f"Scan produced {signal_count} signal(s). "
            f"Real source items: rss={int(source_counts.get('rss_count') or 0)}, "
            f"reddit={int(source_counts.get('reddit_count') or 0)}, x={int(source_counts.get('x_count') or 0)}."
        )
        return

    diagnostics['diagnostic_summary'] = (
        'Scan produced zero signals; review reason codes for source configuration, empty inputs, '
        'or demo fallback decision details.'
    )


def run_scan_agent(*, source_ids: list[int] | None = None, triggered_by: str = 'manual') -> SourceScanRun:
    started_at = timezone.now()
    scan_run = SourceScanRun.objects.create(started_at=started_at, metadata={'triggered_by': triggered_by})
    diagnostics = _base_diagnostics(source_ids=source_ids)

    fetch_result = fetch_parallel_source_items(source_ids=source_ids)
    if len(fetch_result) == 4:
        raw_items, source_counts, fetch_errors, _ = fetch_result
    else:
        raw_items, source_counts, fetch_errors = fetch_result

    fallback_used = False
    fallback_market_ids: list[int] = []
    if not raw_items and is_local_demo_environment():
        if is_scan_demo_fallback_enabled():
            fallback = build_demo_narrative_fallback_items()
            raw_items.extend(fallback.items)
            fallback_market_ids = fallback.market_ids
            if fallback.items:
                fallback_used = True
                diagnostics['zero_signal_reason_codes'].append(SCAN_REASON_DEMO_FALLBACK_USED)
            else:
                diagnostics['zero_signal_reason_codes'].append(SCAN_REASON_DEMO_MODE_NO_NARRATIVE_FIXTURES)
        else:
            diagnostics['zero_signal_reason_codes'].append(SCAN_REASON_DEMO_FALLBACK_DISABLED)

    dedup = deduplicate_narratives(raw_items)
    clusters = cluster_narratives(dedup.deduped_items)

    recommendations_counter: Counter[str] = Counter()
    ignored_count = 0

    for cluster in clusters:
        source_types = {item.source_type for item in cluster.items}
        published_values = [item.published_at or timezone.now() for item in cluster.items]
        first_seen = min(published_values)
        last_seen = max(published_values)

        cluster_obj = NarrativeCluster.objects.create(
            scan_run=scan_run,
            canonical_topic=cluster.topic[:255],
            representative_headline=cluster.representative_headline[:512],
            source_types=sorted(source_types),
            item_count=len(cluster.items),
            first_seen_at=first_seen,
            last_seen_at=last_seen,
            combined_direction='unclear',
            combined_sentiment=NarrativeSentiment.UNCERTAIN,
            cluster_status=_cluster_status(source_types=source_types, item_count=len(cluster.items), last_seen_at=last_seen),
            metadata={'cluster_key': cluster.key},
        )

        scored = score_cluster(cluster)
        market = infer_target_market(cluster.topic)
        divergence, divergence_note = narrative_market_divergence(direction=scored.direction, market=market)
        total_score = Decimal(min(1.0, float(scored.total_signal_score + (divergence * Decimal('0.20'))))).quantize(Decimal('0.0001'))
        status = _signal_status(total_score, scored.direction, divergence)

        reason_codes = list(scored.reason_codes)
        reason_codes.append(divergence_note.upper())

        if market:
            try:
                influence = run_assist(
                    query_text=f'Narrative pattern: {cluster.topic}. Direction={scored.direction}.',
                    query_type=MemoryQueryType.RESEARCH,
                    context_metadata={'source': 'scan_agent', 'market_id': market.id},
                    limit=4,
                )
                if influence.summary.get('matches'):
                    reason_codes.append('PRECEDENT_CONTEXT_ATTACHED')
            except Exception:
                influence = None
        else:
            influence = None

        signal = NarrativeSignal.objects.create(
            scan_run=scan_run,
            canonical_label=cluster.representative_headline[:255],
            topic=cluster.topic[:255],
            target_market=market,
            source_mix={'source_types': sorted(source_types), 'source_count': len(source_types), 'item_count': len(cluster.items)},
            direction=scored.direction,
            sentiment_score=scored.sentiment_score,
            novelty_score=scored.novelty_score,
            intensity_score=scored.intensity_score,
            source_confidence_score=scored.source_confidence_score,
            market_divergence_score=divergence,
            total_signal_score=total_score,
            status=status,
            rationale=f"Topic '{cluster.topic}' scored for {scored.direction} with {divergence_note.replace('_', ' ')}.",
            reason_codes=reason_codes,
            raw_source_refs=[{'title': item.title, 'url': item.url, 'source_type': item.source_type} for item in cluster.items[:12]],
            linked_cluster=cluster_obj,
            linked_market=market,
            metadata={'precedent_summary': influence.summary if influence else {}, 'source_errors': fetch_errors[:4]},
        )
        if fallback_used:
            signal.metadata = {
                **(signal.metadata or {}),
                'fallback_type': 'demo_narrative',
                'is_demo': True,
                'is_synthetic': True,
                'is_fallback': True,
            }
            signal.reason_codes = list(dict.fromkeys([*signal.reason_codes, 'DEMO_SYNTHETIC_FALLBACK']))
            signal.save(update_fields=['metadata', 'reason_codes', 'updated_at'])
        if status == NarrativeSignalStatus.IGNORE:
            ignored_count += 1

        recommendation_type, confidence, rec_codes, blockers, rationale = recommend_for_signal(signal)
        ScanRecommendation.objects.create(
            scan_run=scan_run,
            recommendation_type=recommendation_type,
            target_signal=signal,
            rationale=rationale,
            reason_codes=rec_codes,
            confidence=confidence,
            blockers=blockers,
        )
        recommendations_counter[recommendation_type] += 1

    if fallback_used and not scan_run.signals.filter(status=NarrativeSignalStatus.SHORTLISTED).exists():
        top_fallback_signal = scan_run.signals.order_by('-total_signal_score', '-id').first()
        if top_fallback_signal is not None:
            top_fallback_signal.status = NarrativeSignalStatus.SHORTLISTED
            top_fallback_signal.reason_codes = list(
                dict.fromkeys([*top_fallback_signal.reason_codes, 'DEMO_FALLBACK_SHORTLIST_OVERRIDE'])
            )
            top_fallback_signal.metadata = {
                **(top_fallback_signal.metadata or {}),
                'demo_shortlist_override': True,
            }
            top_fallback_signal.save(update_fields=['status', 'reason_codes', 'metadata', 'updated_at'])

    scan_run.completed_at = timezone.now()
    scan_run.source_counts = source_counts
    scan_run.raw_item_count = len(raw_items)
    scan_run.deduped_item_count = len(dedup.deduped_items)
    scan_run.clustered_count = len(clusters)
    scan_run.signal_count = scan_run.signals.count()
    scan_run.ignored_count = ignored_count + len(dedup.ignored_items)
    scan_run.recommendation_summary = dict(recommendations_counter)

    _finalize_diagnostics(diagnostics=diagnostics, source_counts=source_counts, signal_count=scan_run.signal_count)
    scan_run.metadata = {
        **(scan_run.metadata or {}),
        'fetch_errors': fetch_errors,
        'dedup_ignored': len(dedup.ignored_items),
        'scan_diagnostics': diagnostics,
        'demo_fallback_used': fallback_used,
        'demo_fallback_market_ids': fallback_market_ids,
    }
    scan_run.save(
        update_fields=[
            'completed_at',
            'source_counts',
            'raw_item_count',
            'deduped_item_count',
            'clustered_count',
            'signal_count',
            'ignored_count',
            'recommendation_summary',
            'metadata',
            'updated_at',
        ]
    )
    return scan_run


def _status_for_score(score: Decimal, reason_codes: list[str]):
    hard_blockers = {'market_not_open', 'bad_time_horizon_near_expiry'}
    if any(code in hard_blockers for code in reason_codes):
        return MarketResearchCandidateStatus.IGNORE
    if score >= Decimal('0.72'):
        return MarketResearchCandidateStatus.SHORTLIST
    if score >= Decimal('0.48'):
        return MarketResearchCandidateStatus.WATCHLIST
    if 'no_scan_signals' in reason_codes and score >= Decimal('0.40'):
        return MarketResearchCandidateStatus.NEEDS_REVIEW
    return MarketResearchCandidateStatus.IGNORE


def run_market_universe_triage(*, provider_scope=None, source_scope=None, triggered_by='manual_api'):
    started_at = timezone.now()
    run = MarketUniverseRun.objects.create(started_at=started_at, metadata={'triggered_by': triggered_by})
    markets, provider_counts = fetch_market_universe(provider_scope=provider_scope, source_scope=source_scope)

    status_counter = Counter()
    recommendation_counter = Counter()

    for market in markets:
        structural = evaluate_structural_filters(market=market, now=started_at)
        narrative = link_narrative_signals(market=market)

        precedent_context = {}
        try:
            assist = run_assist(
                query_text=f"{market.title} {market.category}"[:220],
                query_type=MemoryQueryType.RESEARCH,
                context_metadata={'market_id': market.id, 'source': 'research_agent_universe_triage'},
                limit=3,
            )
            precedent_context = {'caution_weight': '0.08' if assist.retrieval_run.result_count > 0 else '0'}
        except Exception:
            precedent_context = {'caution_weight': '0'}

        reason_codes = structural.reason_codes + narrative['reason_codes']
        pursue_score = compute_pursue_worthiness(structural=structural, narrative_context=narrative, precedent_context=precedent_context)
        status = _status_for_score(pursue_score, reason_codes)

        candidate = MarketResearchCandidate.objects.create(
            universe_run=run,
            linked_market=market,
            market_title=market.title,
            market_provider=market.provider.slug,
            category=market.category,
            end_time=market.resolution_time,
            time_to_resolution_hours=structural.time_to_resolution_hours,
            liquidity_score=structural.liquidity_score,
            volume_score=structural.volume_score,
            freshness_score=structural.freshness_score,
            market_quality_score=structural.market_quality_score,
            narrative_support_score=narrative['narrative_support_score'],
            divergence_score=narrative['divergence_score'],
            pursue_worthiness_score=pursue_score,
            status=status,
            rationale=(
                f"open={structural.open_ok}; liquidity={structural.liquidity_score}; volume={structural.volume_score}; "
                f"freshness={structural.freshness_score}; narrative={narrative['narrative_support_score']}; divergence={narrative['divergence_score']}"
            ),
            reason_codes=reason_codes,
            linked_narrative_signals=narrative['linked_signals'],
            metadata={'blockers': structural.blockers, 'precedent_context': precedent_context},
        )
        status_counter[status] += 1

        decision_payload = decision_for_candidate(candidate=candidate)
        MarketTriageDecisionV2.objects.create(
            linked_candidate=candidate,
            decision_type=decision_payload['decision_type'],
            decision_status=decision_payload['decision_status'],
            rationale=candidate.rationale,
            reason_codes=candidate.reason_codes,
            blockers=candidate.metadata.get('blockers', []),
            metadata={'pursue_worthiness_score': str(candidate.pursue_worthiness_score)},
        )
        MarketResearchRecommendation.objects.create(
            universe_run=run,
            recommendation_type=decision_payload['recommendation_type'],
            target_market=market,
            target_candidate=candidate,
            rationale=candidate.rationale,
            reason_codes=candidate.reason_codes,
            confidence=decision_payload['confidence'],
            blockers=candidate.metadata.get('blockers', []),
        )
        recommendation_counter[decision_payload['recommendation_type']] += 1

    run.total_markets_seen = len(markets)
    run.open_markets_seen = sum(1 for market in markets if market.status == 'open')
    run.shortlisted_count = status_counter[MarketResearchCandidateStatus.SHORTLIST]
    run.watchlist_count = status_counter[MarketResearchCandidateStatus.WATCHLIST]
    run.ignored_count = status_counter[MarketResearchCandidateStatus.IGNORE]
    run.filtered_out_count = run.ignored_count
    run.source_provider_counts = provider_counts
    run.recommendation_summary = dict(recommendation_counter)
    run.completed_at = timezone.now()
    run.metadata = {
        **(run.metadata or {}),
        'provider_scope': provider_scope or [],
        'source_scope': source_scope or [],
    }
    run.save()
    return run


def get_latest_universe_summary():
    run = MarketUniverseRun.objects.order_by('-started_at', '-id').first()
    if not run:
        return {
            'latest_run': None,
            'totals': {
                'total_markets_seen': 0,
                'open_markets_seen': 0,
                'shortlisted_count': 0,
                'watchlist_count': 0,
                'ignored_count': 0,
                'sent_to_prediction_count': 0,
            },
            'recommendation_summary': {},
        }

    sent_count = run.recommendations.filter(recommendation_type='send_to_prediction').count()
    return {
        'latest_run': {
            'id': run.id,
            'started_at': run.started_at,
            'completed_at': run.completed_at,
        },
        'totals': {
            'total_markets_seen': run.total_markets_seen,
            'open_markets_seen': run.open_markets_seen,
            'shortlisted_count': run.shortlisted_count,
            'watchlist_count': run.watchlist_count,
            'ignored_count': run.ignored_count,
            'sent_to_prediction_count': sent_count,
        },
        'recommendation_summary': run.recommendation_summary,
    }

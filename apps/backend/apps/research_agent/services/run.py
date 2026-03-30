from __future__ import annotations

from collections import Counter
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from apps.memory_retrieval.models import MemoryQueryType
from apps.memory_retrieval.services import run_assist
from apps.research_agent.models import (
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
from apps.research_agent.services.market_context import infer_target_market, narrative_market_divergence
from apps.research_agent.services.recommendation import recommend_for_signal
from apps.research_agent.services.scoring import score_cluster
from apps.research_agent.services.source_fetch import fetch_parallel_source_items


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


def run_scan_agent(*, source_ids: list[int] | None = None, triggered_by: str = 'manual') -> SourceScanRun:
    started_at = timezone.now()
    scan_run = SourceScanRun.objects.create(started_at=started_at, metadata={'triggered_by': triggered_by})

    raw_items, source_counts, fetch_errors = fetch_parallel_source_items(source_ids=source_ids)
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

    scan_run.completed_at = timezone.now()
    scan_run.source_counts = source_counts
    scan_run.raw_item_count = len(raw_items)
    scan_run.deduped_item_count = len(dedup.deduped_items)
    scan_run.clustered_count = len(clusters)
    scan_run.signal_count = scan_run.signals.count()
    scan_run.ignored_count = ignored_count + len(dedup.ignored_items)
    scan_run.recommendation_summary = dict(recommendations_counter)
    scan_run.metadata = {
        **(scan_run.metadata or {}),
        'fetch_errors': fetch_errors,
        'dedup_ignored': len(dedup.ignored_items),
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

from __future__ import annotations

from collections import Counter
from decimal import Decimal

from apps.research_agent.models import NarrativeBias, NarrativeConsensusRecord, NarrativeConsensusState, NarrativeSignal


def _bias_for_direction(direction: str) -> str:
    if direction == 'bullish_yes':
        return NarrativeBias.BULLISH
    if direction == 'bearish_yes':
        return NarrativeBias.BEARISH
    if direction == 'mixed':
        return NarrativeBias.MIXED
    return NarrativeBias.UNCLEAR


def build_consensus_records(*, run, signals):
    records = []
    grouped = {}
    for signal in signals:
        key = signal.linked_cluster_id or f"topic::{signal.topic.lower()}"
        grouped.setdefault(key, []).append(signal)

    for cluster_signals in grouped.values():
        primary = cluster_signals[0]
        source_types = set()
        direction_counter = Counter()
        intensity = Decimal('0.0000')
        novelty = Decimal('0.0000')
        persistence = Decimal('0.0000')
        confidence = Decimal('0.0000')

        for signal in cluster_signals:
            mix = signal.source_mix or {}
            source_types.update(mix.get('source_types') or [])
            direction_counter[_bias_for_direction(signal.direction)] += 1
            intensity += signal.intensity_score
            novelty += signal.novelty_score
            persistence += Decimal(str(min(1.0, float((mix.get('item_count') or 0) / 6))))
            confidence += signal.source_confidence_score

        count = len(cluster_signals)
        source_count = len(source_types)
        top_direction, top_count = direction_counter.most_common(1)[0] if direction_counter else (NarrativeBias.UNCLEAR, 0)
        dominant_ratio = (Decimal(top_count) / Decimal(count)) if count else Decimal('0')

        if count < 2 or source_count == 0:
            state = NarrativeConsensusState.INSUFFICIENT_SIGNAL
        elif source_count >= 2 and dominant_ratio >= Decimal('0.75'):
            state = NarrativeConsensusState.STRONG_CONSENSUS
        elif source_count >= 2 and dominant_ratio >= Decimal('0.55'):
            state = NarrativeConsensusState.WEAK_CONSENSUS
        elif NarrativeBias.BULLISH in direction_counter and NarrativeBias.BEARISH in direction_counter:
            state = NarrativeConsensusState.CONFLICTED
        else:
            state = NarrativeConsensusState.MIXED

        record = NarrativeConsensusRecord.objects.create(
            consensus_run=run,
            linked_cluster=primary.linked_cluster,
            topic_label=primary.topic[:255],
            source_mix={
                'source_types': sorted(source_types),
                'signal_ids': [signal.id for signal in cluster_signals],
                'source_distribution': dict(Counter((s.source_mix or {}).get('source_count', 0) for s in cluster_signals)),
            },
            source_count=source_count,
            consensus_state=state,
            sentiment_direction=top_direction,
            intensity_score=(intensity / Decimal(count)).quantize(Decimal('0.0001')),
            novelty_score=(novelty / Decimal(count)).quantize(Decimal('0.0001')),
            persistence_score=(persistence / Decimal(count)).quantize(Decimal('0.0001')),
            confidence_score=(confidence / Decimal(count)).quantize(Decimal('0.0001')),
            summary=f"Consensus {state} for topic '{primary.topic}' across {source_count} source types and {count} linked scan signals.",
            metadata={'linked_signal_ids': [signal.id for signal in cluster_signals]},
        )
        records.append(record)

    return records

from __future__ import annotations

from decimal import Decimal

from apps.research_agent.models import NarrativeBias, NarrativeDivergenceState, NarrativeMarketDivergenceRecord


def build_divergence_records(*, run, consensus_records):
    records = []
    for record in consensus_records:
        signal_ids = (record.metadata or {}).get('linked_signal_ids') or []
        signal = record.linked_cluster.signals.filter(id__in=signal_ids).select_related('linked_market').order_by('-total_signal_score').first() if record.linked_cluster else None
        linked_market = signal.linked_market if signal else None
        market_probability = None
        if linked_market and linked_market.current_market_probability is not None:
            market_probability = Decimal(str(linked_market.current_market_probability)).quantize(Decimal('0.0001'))

        narrative_score = record.confidence_score
        if record.sentiment_direction == NarrativeBias.BULLISH:
            narrative_probability = Decimal('0.50') + (narrative_score / Decimal('2.5'))
        elif record.sentiment_direction == NarrativeBias.BEARISH:
            narrative_probability = Decimal('0.50') - (narrative_score / Decimal('2.5'))
        else:
            narrative_probability = Decimal('0.50')

        if market_probability is None or record.sentiment_direction in {NarrativeBias.MIXED, NarrativeBias.UNCLEAR}:
            divergence_state = NarrativeDivergenceState.UNCERTAIN
            divergence_score = Decimal('0.0000')
        else:
            divergence_score = abs((narrative_probability - market_probability)).quantize(Decimal('0.0001'))
            if divergence_score >= Decimal('0.2500'):
                divergence_state = NarrativeDivergenceState.HIGH_DIVERGENCE
            elif divergence_score >= Decimal('0.1200'):
                divergence_state = NarrativeDivergenceState.MODEST_DIVERGENCE
            else:
                divergence_state = NarrativeDivergenceState.ALIGNED

        divergence = NarrativeMarketDivergenceRecord.objects.create(
            consensus_run=run,
            linked_consensus_record=record,
            linked_market=linked_market,
            market_probability=market_probability,
            narrative_bias=record.sentiment_direction,
            divergence_state=divergence_state,
            divergence_score=divergence_score,
            market_context_summary=(
                f"Narrative bias={record.sentiment_direction}, market_probability={market_probability if market_probability is not None else 'n/a'}, state={divergence_state}."
            ),
            metadata={'narrative_probability_proxy': str(narrative_probability)},
        )
        records.append(divergence)
    return records

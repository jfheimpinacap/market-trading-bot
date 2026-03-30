from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from apps.research_agent.services.clustering import ClusterBundle


@dataclass
class SignalScore:
    direction: str
    sentiment_score: Decimal
    novelty_score: Decimal
    intensity_score: Decimal
    source_confidence_score: Decimal
    total_signal_score: Decimal
    reason_codes: list[str]


def _clamp(value: float) -> Decimal:
    return Decimal(f'{max(0.0, min(value, 1.0)):.4f}')


def score_cluster(cluster: ClusterBundle) -> SignalScore:
    source_types = {item.source_type for item in cluster.items}
    source_count = len(source_types)
    item_count = len(cluster.items)
    combined_text = ' '.join(item.raw_text.lower() for item in cluster.items)
    bullish_hits = sum(token in combined_text for token in ['surge', 'upside', 'rise', 'beat', 'bull'])
    bearish_hits = sum(token in combined_text for token in ['drop', 'downside', 'miss', 'bear', 'risk-off'])

    if bullish_hits and bearish_hits:
        direction = 'mixed'
    elif bullish_hits > bearish_hits:
        direction = 'bullish_yes'
    elif bearish_hits > bullish_hits:
        direction = 'bearish_yes'
    else:
        direction = 'unclear'

    source_confidence = _clamp(0.35 + (0.25 * source_count))
    novelty = _clamp(1.0 - (0.08 * max(item_count - 1, 0)))
    intensity = _clamp(min(1.0, (item_count / 4.0) + (0.08 * source_count)))
    sentiment = _clamp(0.5 + 0.1 * (bullish_hits - bearish_hits))

    total = _clamp(float((Decimal('0.30') * source_confidence) + (Decimal('0.25') * novelty) + (Decimal('0.25') * intensity) + (Decimal('0.20') * sentiment)))

    reason_codes: list[str] = []
    if source_count > 1:
        reason_codes.append('MULTI_SOURCE_OVERLAP')
    if novelty < Decimal('0.4000'):
        reason_codes.append('LOW_NOVELTY_STALE')
    if direction == 'unclear':
        reason_codes.append('DIRECTION_UNCLEAR')

    return SignalScore(
        direction=direction,
        sentiment_score=sentiment,
        novelty_score=novelty,
        intensity_score=intensity,
        source_confidence_score=source_confidence,
        total_signal_score=total,
        reason_codes=reason_codes,
    )

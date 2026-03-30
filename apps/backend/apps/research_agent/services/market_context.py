from __future__ import annotations

from decimal import Decimal

from apps.markets.models import Market


def infer_target_market(topic: str) -> Market | None:
    if not topic:
        return None
    candidates = Market.objects.filter(is_active=True, title__icontains=topic.split(' ')[0]).order_by('-updated_at', '-id')
    return candidates.first()


def narrative_market_divergence(*, direction: str, market: Market | None) -> tuple[Decimal, str]:
    if market is None or market.current_market_probability is None:
        return Decimal('0.2000'), 'no_market_context'
    probability = Decimal(market.current_market_probability)
    if direction == 'bullish_yes':
        divergence = max(Decimal('0.0000'), Decimal('0.7000') - probability)
    elif direction == 'bearish_yes':
        divergence = max(Decimal('0.0000'), probability - Decimal('0.3000'))
    else:
        divergence = Decimal('0.1500')
    if divergence >= Decimal('0.3000'):
        return divergence.quantize(Decimal('0.0001')), 'high_divergence'
    if divergence <= Decimal('0.1000'):
        return divergence.quantize(Decimal('0.0001')), 'already_priced'
    return divergence.quantize(Decimal('0.0001')), 'moderate_divergence'

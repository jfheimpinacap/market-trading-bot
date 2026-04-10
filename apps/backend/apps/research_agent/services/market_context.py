from __future__ import annotations

from decimal import Decimal
import re

from apps.markets.models import Market


_STOP_TOKENS = {
    'the',
    'and',
    'for',
    'with',
    'will',
    'from',
    'that',
    'this',
    'into',
    'about',
    'over',
}


def _topic_tokens(topic: str) -> list[str]:
    normalized = re.sub(r'[^a-z0-9\s]+', ' ', str(topic or '').lower())
    return [token for token in normalized.split() if len(token) >= 3 and token not in _STOP_TOKENS]


def infer_target_market(topic: str) -> Market | None:
    if not topic:
        return None
    tokens = _topic_tokens(topic)
    if not tokens:
        return None

    candidates = list(Market.objects.filter(is_active=True).order_by('-updated_at', '-id')[:300])
    scored: list[tuple[Decimal, Market]] = []
    for market in candidates:
        corpus = ' '.join(
            [
                str(market.title or ''),
                str(market.category or ''),
                str(market.ticker or ''),
                str(market.slug or ''),
            ]
        ).lower()
        token_hits = sum(1 for token in tokens if token in corpus)
        if token_hits == 0:
            continue
        score = Decimal(token_hits)
        if (market.source_type or '') == 'demo':
            score += Decimal('0.20')
        if (market.status or '') == 'open':
            score += Decimal('0.20')
        scored.append((score, market))

    if not scored:
        return None

    scored.sort(key=lambda row: (row[0], row[1].updated_at, row[1].id), reverse=True)
    top_score, top_market = scored[0]
    second_score = scored[1][0] if len(scored) > 1 else Decimal('0')
    if top_score < Decimal('1.00'):
        return None
    if len(scored) > 1 and top_score == second_score:
        return None
    return top_market


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

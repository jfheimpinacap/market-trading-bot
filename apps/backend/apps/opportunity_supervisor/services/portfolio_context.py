from __future__ import annotations

from decimal import Decimal

from apps.portfolio_governor.services import get_latest_throttle_decision


def build_portfolio_fit(*, provider: str, category: str) -> tuple[Decimal, dict]:
    throttle = get_latest_throttle_decision()
    if not throttle:
        return Decimal('0.7000'), {'throttle_state': 'NORMAL', 'provider': provider, 'category': category}

    score = Decimal('0.7000')
    if throttle.state == 'BLOCK_NEW_ENTRIES':
        score = Decimal('0.2000')
    elif throttle.state == 'THROTTLE':
        score = Decimal('0.4500')

    return score, {
        'throttle_state': throttle.state,
        'recommended_multiplier': str(throttle.recommended_max_size_multiplier),
        'provider': provider,
        'category': category,
    }

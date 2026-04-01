from __future__ import annotations

from decimal import Decimal

from apps.autonomous_trader.models import AutonomousSizingContext


MIN_NOTIONAL = Decimal('10.00')
BASE_CAPITAL = Decimal('1000.00')


def apply_conservative_adjustments(*, context: AutonomousSizingContext, applied_fraction: Decimal) -> tuple[Decimal, list[str], str]:
    reason_codes: list[str] = []
    fraction = applied_fraction
    method = 'KELLY_CAPPED'

    if context.context_status == 'BLOCKED' or context.risk_posture == 'BLOCKED':
        return Decimal('0.00'), ['RISK_BLOCK'], 'FIXED_NOTIONAL'

    if context.context_status == 'INSUFFICIENT_CONTEXT':
        return MIN_NOTIONAL, ['INSUFFICIENT_CONTEXT_FALLBACK'], 'FIXED_NOTIONAL'

    if context.confidence < Decimal('0.60'):
        fraction *= Decimal('0.60')
        reason_codes.append('CONFIDENCE_DISCOUNT')
        method = 'RISK_REDUCED_FRACTIONAL'

    if context.uncertainty is not None and context.uncertainty > Decimal('0.35'):
        fraction *= Decimal('0.65')
        reason_codes.append('UNCERTAINTY_DISCOUNT')
        method = 'RISK_REDUCED_FRACTIONAL'

    if context.linked_feedback_influence and context.linked_feedback_influence.influence_type in {'CAUTION_BOOST', 'CONFIDENCE_REDUCTION'}:
        fraction *= Decimal('0.75')
        reason_codes.append('FEEDBACK_CAUTION_DISCOUNT')

    if context.portfolio_posture in {'CAUTION', 'THROTTLED'}:
        fraction *= Decimal('0.70')
        reason_codes.append('PORTFOLIO_CAP')
        method = 'PORTFOLIO_THROTTLED'
    elif context.portfolio_posture == 'BLOCK_NEW_ENTRIES':
        return Decimal('0.00'), ['PORTFOLIO_BLOCK_NEW_ENTRIES'], 'PORTFOLIO_THROTTLED'

    notional = (BASE_CAPITAL * max(Decimal('0.00'), fraction)).quantize(Decimal('0.01'))
    if notional < MIN_NOTIONAL and notional > 0:
        notional = MIN_NOTIONAL
        reason_codes.append('MIN_NOTIONAL_FLOOR')
    return notional, reason_codes, method

from __future__ import annotations

from decimal import Decimal


def bounded_fractional_kelly(*, edge: Decimal, confidence: Decimal, uncertainty: Decimal | None = None) -> tuple[Decimal, Decimal]:
    if edge <= Decimal('0'):
        return Decimal('0'), Decimal('0')

    confidence_factor = max(Decimal('0.25'), min(Decimal('1.0'), confidence))
    uncertainty_factor = Decimal('1.0')
    if uncertainty is not None:
        uncertainty_factor = max(Decimal('0.40'), min(Decimal('1.00'), Decimal('1.00') - uncertainty))

    base_kelly = max(Decimal('0.00'), min(Decimal('0.25'), edge * Decimal('1.5')))
    fractional = (base_kelly * Decimal('0.35') * confidence_factor * uncertainty_factor).quantize(Decimal('0.000001'))
    capped = max(Decimal('0.000000'), min(Decimal('0.050000'), fractional))
    return base_kelly.quantize(Decimal('0.000001')), capped

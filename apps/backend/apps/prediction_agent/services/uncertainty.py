from __future__ import annotations

from decimal import Decimal


def apply_uncertainty_adjustments(*, confidence: Decimal, adjusted_edge: Decimal, narrative_priority: Decimal, precedent_caution: Decimal, uncertainty: Decimal) -> tuple[Decimal, Decimal, list[str]]:
    reason_codes: list[str] = []
    confidence_out = Decimal(str(confidence))
    edge_out = Decimal(str(adjusted_edge))

    if uncertainty >= Decimal('0.7000'):
        confidence_out -= Decimal('0.1500')
        reason_codes.append('MODEL_CONFIDENCE_DISCOUNT')

    if narrative_priority < Decimal('0.4000'):
        confidence_out -= Decimal('0.0800')
        reason_codes.append('NARRATIVE_CONFLICT_DISCOUNT')

    if precedent_caution >= Decimal('0.6000'):
        confidence_out -= Decimal('0.0700')
        edge_out -= Decimal('0.0150')
        reason_codes.append('PRECEDENT_CAUTION_DISCOUNT')

    confidence_out = max(Decimal('0.0100'), min(Decimal('0.9900'), confidence_out))
    edge_out = max(Decimal('-0.9900'), min(Decimal('0.9900'), edge_out))
    return confidence_out.quantize(Decimal('0.0001')), edge_out.quantize(Decimal('0.0001')), reason_codes

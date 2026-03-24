from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from apps.learning_memory.models import LearningAdjustment, LearningAdjustmentType, LearningScopeType


@dataclass
class LearningInfluence:
    confidence_delta: Decimal
    quantity_multiplier: Decimal
    caution_delta: Decimal
    reasons: list[str]


def _q4(value: Decimal) -> Decimal:
    return value.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)


def _collect_adjustments(*, market=None, signal_type: str | None = None, source_type: str | None = None):
    scopes = [(LearningScopeType.GLOBAL, 'global')]
    if market is not None:
        scopes.append((LearningScopeType.MARKET, market.slug))
        if market.provider_id:
            scopes.append((LearningScopeType.PROVIDER, market.provider.slug))
        scopes.append((LearningScopeType.SOURCE_TYPE, market.source_type))
    if signal_type:
        scopes.append((LearningScopeType.SIGNAL_TYPE, signal_type))
    if source_type:
        scopes.append((LearningScopeType.SOURCE_TYPE, source_type))

    query = LearningAdjustment.objects.filter(is_active=True)
    predicates = None
    from django.db.models import Q

    for scope_type, scope_key in scopes:
        clause = Q(scope_type=scope_type, scope_key=scope_key)
        predicates = clause if predicates is None else predicates | clause

    if predicates is None:
        return LearningAdjustment.objects.none()
    return query.filter(predicates)


def build_learning_influence(*, market=None, signal_type: str | None = None, source_type: str | None = None) -> LearningInfluence:
    confidence_delta = Decimal('0.0000')
    quantity_multiplier = Decimal('1.0000')
    caution_delta = Decimal('0.0000')
    reasons: list[str] = []

    for adjustment in _collect_adjustments(market=market, signal_type=signal_type, source_type=source_type):
        if adjustment.adjustment_type == LearningAdjustmentType.CONFIDENCE_BIAS:
            confidence_delta += adjustment.magnitude
        elif adjustment.adjustment_type == LearningAdjustmentType.QUANTITY_BIAS:
            quantity_multiplier += adjustment.magnitude
        elif adjustment.adjustment_type in {LearningAdjustmentType.RISK_CAUTION_BIAS, LearningAdjustmentType.POLICY_CAUTION_BIAS}:
            caution_delta += abs(adjustment.magnitude)
        reasons.append(f'{adjustment.adjustment_type} {adjustment.scope_type}:{adjustment.scope_key} {adjustment.magnitude}')

    quantity_multiplier = max(Decimal('0.6000'), min(quantity_multiplier, Decimal('1.0500')))
    confidence_delta = max(Decimal('-0.1500'), min(confidence_delta, Decimal('0.0500')))
    caution_delta = max(Decimal('0.0000'), min(caution_delta, Decimal('0.2000')))

    return LearningInfluence(
        confidence_delta=_q4(confidence_delta),
        quantity_multiplier=_q4(quantity_multiplier),
        caution_delta=_q4(caution_delta),
        reasons=reasons,
    )

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP


def q4(value: Decimal) -> Decimal:
    return value.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)


def clamp_probability(value: Decimal) -> Decimal:
    return max(Decimal('0.0001'), min(Decimal('0.9999'), value))


def apply_linear_calibration(*, probability: Decimal, alpha: Decimal, beta: Decimal) -> Decimal:
    calibrated = (probability * alpha) + beta
    return clamp_probability(q4(calibrated))


def classify_edge(edge: Decimal, *, strong_threshold: Decimal, neutral_threshold: Decimal) -> str:
    absolute = abs(edge)
    if absolute >= strong_threshold:
        return 'positive' if edge > 0 else 'negative'
    if absolute <= neutral_threshold:
        return 'neutral'
    return 'positive' if edge > 0 else 'negative'


def confidence_level(confidence: Decimal) -> str:
    if confidence >= Decimal('0.7000'):
        return 'high'
    if confidence >= Decimal('0.4500'):
        return 'medium'
    return 'low'

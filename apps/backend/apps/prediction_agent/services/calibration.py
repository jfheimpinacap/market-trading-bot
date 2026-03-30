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


def runtime_calibrated_probability(*, system_probability: Decimal, evidence_quality_score: Decimal, uncertainty_score: Decimal) -> Decimal:
    conservative_pull = Decimal('0.08') + (uncertainty_score * Decimal('0.20'))
    evidence_bonus = (evidence_quality_score - Decimal('0.5000')) * Decimal('0.10')
    pull = max(Decimal('0.0000'), conservative_pull - evidence_bonus)
    centered = Decimal('0.5000') + ((system_probability - Decimal('0.5000')) * (Decimal('1.0000') - pull))
    return clamp_probability(q4(centered))


def runtime_confidence_uncertainty(*, edge: Decimal, evidence_quality_score: Decimal, precedent_caution_score: Decimal, signal_conflict_score: Decimal) -> tuple[Decimal, Decimal]:
    uncertainty = Decimal('0.3000')
    uncertainty += (Decimal('1.0000') - evidence_quality_score) * Decimal('0.3500')
    uncertainty += precedent_caution_score * Decimal('0.2500')
    uncertainty += signal_conflict_score * Decimal('0.2500')
    uncertainty = clamp_probability(q4(uncertainty))

    confidence = Decimal('0.3000') + min(abs(edge) * Decimal('2.0000'), Decimal('0.3000'))
    confidence += evidence_quality_score * Decimal('0.2500')
    confidence -= precedent_caution_score * Decimal('0.1800')
    confidence -= signal_conflict_score * Decimal('0.1800')
    confidence = clamp_probability(q4(confidence))
    return confidence, uncertainty

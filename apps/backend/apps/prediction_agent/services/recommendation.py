from __future__ import annotations

from decimal import Decimal

from apps.prediction_agent.models import (
    PredictionAssessmentStatus,
    PredictionRuntimeAssessment,
    PredictionRuntimeRecommendationType,
)


def resolve_prediction_status(*, adjusted_edge: Decimal, confidence_score: Decimal, evidence_quality_score: Decimal, signal_conflict_score: Decimal) -> str:
    abs_edge = abs(adjusted_edge)
    if signal_conflict_score >= Decimal('0.5500'):
        return PredictionAssessmentStatus.CONFLICTED
    if confidence_score < Decimal('0.4200'):
        return PredictionAssessmentStatus.LOW_CONFIDENCE
    if abs_edge < Decimal('0.0200'):
        return PredictionAssessmentStatus.NO_EDGE
    if evidence_quality_score < Decimal('0.3500'):
        return PredictionAssessmentStatus.NEEDS_REVIEW
    if abs_edge >= Decimal('0.0800') and confidence_score >= Decimal('0.6000'):
        return PredictionAssessmentStatus.STRONG_EDGE
    return PredictionAssessmentStatus.WEAK_EDGE


def build_recommendation(assessment: PredictionRuntimeAssessment) -> tuple[str, list[str], Decimal, list[str], str]:
    reason_codes = list(assessment.reason_codes or [])
    blockers: list[str] = []

    if assessment.prediction_status == PredictionAssessmentStatus.STRONG_EDGE:
        reason_codes.append('EDGE_AND_CONFIDENCE_STRONG')
        return (
            PredictionRuntimeRecommendationType.SEND_TO_RISK_ASSESSMENT,
            reason_codes,
            Decimal('0.7600'),
            blockers,
            'Assessment presents strong adjusted edge with sufficient confidence and evidence.',
        )
    if assessment.prediction_status == PredictionAssessmentStatus.WEAK_EDGE:
        reason_codes.append('EDGE_PRESENT_BUT_NOT_STRONG')
        return (
            PredictionRuntimeRecommendationType.SEND_TO_SIGNAL_FUSION,
            reason_codes,
            Decimal('0.6200'),
            blockers,
            'Assessment may be useful for signal fusion, but does not yet justify direct risk handoff.',
        )
    if assessment.prediction_status == PredictionAssessmentStatus.NO_EDGE:
        reason_codes.append('NO_MEANINGFUL_EDGE')
        return (
            PredictionRuntimeRecommendationType.IGNORE_NO_EDGE,
            reason_codes,
            Decimal('0.6800'),
            ['no_edge'],
            'System and market probability are too close after calibration and context adjustment.',
        )
    if assessment.prediction_status == PredictionAssessmentStatus.LOW_CONFIDENCE:
        reason_codes.append('CONFIDENCE_BELOW_RUNTIME_THRESHOLD')
        return (
            PredictionRuntimeRecommendationType.IGNORE_LOW_CONFIDENCE,
            reason_codes,
            Decimal('0.7000'),
            ['low_confidence'],
            'Confidence is too low for reliable downstream usage in this runtime review.',
        )
    if assessment.prediction_status == PredictionAssessmentStatus.CONFLICTED:
        reason_codes.append('SIGNALS_CONFLICT_REQUIRE_MANUAL_REVIEW')
        return (
            PredictionRuntimeRecommendationType.REQUIRE_MANUAL_PREDICTION_REVIEW,
            reason_codes,
            Decimal('0.5800'),
            ['signal_conflict'],
            'High narrative/market divergence increases uncertainty and requires manual review.',
        )

    reason_codes.append('EVIDENCE_WEAK_MONITOR')
    return (
        PredictionRuntimeRecommendationType.KEEP_FOR_MONITORING,
        reason_codes,
        Decimal('0.5400'),
        ['needs_review'],
        'Assessment is currently better suited for monitoring than escalation.',
    )

from __future__ import annotations

from decimal import Decimal

from apps.prediction_agent.models import (
    PredictionAssessmentStatus,
    PredictionConvictionReview,
    PredictionConvictionReviewStatus,
    PredictionIntakeRecommendation,
    PredictionIntakeRecommendationType,
    PredictionIntakeRun,
    PredictionRuntimeAssessment,
    PredictionRuntimeRecommendationType,
    RiskReadyPredictionHandoff,
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


def create_intake_recommendation(*, intake_run: PredictionIntakeRun, review: PredictionConvictionReview, handoff: RiskReadyPredictionHandoff) -> PredictionIntakeRecommendation:
    recommendation_type = PredictionIntakeRecommendationType.KEEP_FOR_MONITORING
    blockers: list[str] = []

    if review.review_status == PredictionConvictionReviewStatus.READY_FOR_RISK:
        recommendation_type = PredictionIntakeRecommendationType.SEND_TO_RISK_IMMEDIATELY
    elif review.review_status == PredictionConvictionReviewStatus.IGNORE_NO_EDGE:
        recommendation_type = PredictionIntakeRecommendationType.IGNORE_FOR_NO_EDGE
        blockers.append('no_edge')
    elif review.review_status == PredictionConvictionReviewStatus.IGNORE_LOW_CONFIDENCE:
        recommendation_type = PredictionIntakeRecommendationType.IGNORE_FOR_LOW_CONFIDENCE
        blockers.append('low_confidence')
    elif review.review_status == PredictionConvictionReviewStatus.REQUIRE_MANUAL_PREDICTION_REVIEW:
        recommendation_type = PredictionIntakeRecommendationType.REQUIRE_MANUAL_REVIEW_FOR_PREDICTION_CONFLICT
        blockers.append('manual_review')
    elif 'NARRATIVE_CONFLICT_DISCOUNT' in (review.reason_codes or []):
        recommendation_type = PredictionIntakeRecommendationType.REDUCE_CONFIDENCE_FOR_NARRATIVE_CONFLICT
    elif 'PRECEDENT_CAUTION_DISCOUNT' in (review.reason_codes or []):
        recommendation_type = PredictionIntakeRecommendationType.REDUCE_CONFIDENCE_FOR_PRECEDENT_CAUTION

    return PredictionIntakeRecommendation.objects.create(
        intake_run=intake_run,
        recommendation_type=recommendation_type,
        target_market=review.linked_intake_candidate.linked_market,
        target_intake_candidate=review.linked_intake_candidate,
        target_conviction_review=review,
        target_handoff=handoff,
        rationale=f'Intake recommendation generated from conviction review status={review.review_status}.',
        reason_codes=list(review.reason_codes or []),
        confidence=review.confidence,
        blockers=blockers,
    )

from __future__ import annotations

from decimal import Decimal

from apps.prediction_agent.models import (
    PredictionConvictionBucket,
    PredictionConvictionReview,
    PredictionConvictionReviewStatus,
    PredictionIntakeCandidate,
)
from apps.prediction_agent.services.calibration import q4, runtime_calibrated_probability, runtime_confidence_uncertainty
from apps.prediction_agent.services.context_adjustment import apply_context_adjustment
from apps.prediction_agent.services.features import build_prediction_features
from apps.prediction_agent.services.model_runtime import resolve_runtime_probability
from apps.prediction_agent.services.uncertainty import apply_uncertainty_adjustments


def _as_score(value: Decimal | None, default: str = '0.5000') -> Decimal:
    raw = Decimal(str(value if value is not None else default))
    return max(Decimal('0.0001'), min(Decimal('0.9999'), raw))


def review_candidate(*, intake_candidate: PredictionIntakeCandidate) -> PredictionConvictionReview:
    feature_result = build_prediction_features(market=intake_candidate.linked_market)
    feature_summary = feature_result.snapshot or {}

    market_probability = _as_score(intake_candidate.linked_market.current_market_probability)
    narrative_priority = _as_score(intake_candidate.narrative_priority)
    divergence_score = _as_score(getattr(intake_candidate.linked_divergence_record, 'divergence_score', None), '0.0000')
    evidence_quality = _as_score((intake_candidate.structural_priority + intake_candidate.handoff_confidence) / Decimal('2'))

    runtime_model = resolve_runtime_probability(
        market_probability=market_probability,
        narrative_support_score=narrative_priority,
        divergence_score=divergence_score,
        candidate_quality_score=evidence_quality,
        feature_summary=feature_summary,
    )
    context = apply_context_adjustment(
        market_id=intake_candidate.linked_market_id,
        market_probability=market_probability,
        calibrated_probability=runtime_model.system_probability,
        narrative_support_score=narrative_priority,
        divergence_score=divergence_score,
    )

    confidence, uncertainty = runtime_confidence_uncertainty(
        edge=q4(runtime_model.system_probability - market_probability),
        evidence_quality_score=evidence_quality,
        precedent_caution_score=context.precedent_caution_score,
        signal_conflict_score=context.signal_conflict_score,
    )
    calibrated_probability = runtime_calibrated_probability(
        system_probability=runtime_model.system_probability,
        evidence_quality_score=evidence_quality,
        uncertainty_score=uncertainty,
    )
    raw_edge = q4(calibrated_probability - market_probability)
    adjusted_edge = q4(raw_edge + context.narrative_influence_score - (context.precedent_caution_score * Decimal('0.25')))
    adjusted_confidence, adjusted_edge, uncertainty_codes = apply_uncertainty_adjustments(
        confidence=confidence,
        adjusted_edge=adjusted_edge,
        narrative_priority=narrative_priority,
        precedent_caution=context.precedent_caution_score,
        uncertainty=uncertainty,
    )

    abs_edge = abs(adjusted_edge)
    if abs_edge >= Decimal('0.0800') and adjusted_confidence >= Decimal('0.6500'):
        bucket = PredictionConvictionBucket.HIGH_CONVICTION
        status = PredictionConvictionReviewStatus.READY_FOR_RISK
    elif abs_edge >= Decimal('0.0400') and adjusted_confidence >= Decimal('0.5200'):
        bucket = PredictionConvictionBucket.MEDIUM_CONVICTION
        status = PredictionConvictionReviewStatus.KEEP_FOR_MONITORING
    elif abs_edge < Decimal('0.0200'):
        bucket = PredictionConvictionBucket.NO_CONVICTION
        status = PredictionConvictionReviewStatus.IGNORE_NO_EDGE
    elif adjusted_confidence < Decimal('0.4200'):
        bucket = PredictionConvictionBucket.LOW_CONVICTION
        status = PredictionConvictionReviewStatus.IGNORE_LOW_CONFIDENCE
    else:
        bucket = PredictionConvictionBucket.LOW_CONVICTION
        status = PredictionConvictionReviewStatus.REQUIRE_MANUAL_PREDICTION_REVIEW

    return PredictionConvictionReview.objects.create(
        linked_intake_candidate=intake_candidate,
        system_probability=runtime_model.system_probability,
        market_probability=market_probability,
        calibrated_probability=calibrated_probability,
        raw_edge=raw_edge,
        adjusted_edge=adjusted_edge,
        confidence=adjusted_confidence,
        uncertainty=uncertainty,
        conviction_bucket=bucket,
        review_status=status,
        review_summary=(
            f'Calibrated conviction review: edge={adjusted_edge}, confidence={adjusted_confidence}, '
            f'uncertainty={uncertainty}, status={status}.'
        ),
        reason_codes=[*runtime_model.reason_codes, *context.reason_codes, *uncertainty_codes],
        metadata={
            'model_mode': runtime_model.model_mode,
            'feature_summary': feature_summary,
            'stale_market_data': feature_result.stale_market_data,
        },
    )

from __future__ import annotations

from apps.prediction_agent.models import (
    PredictionConvictionReview,
    PredictionConvictionReviewStatus,
    RiskReadyPredictionHandoff,
    RiskReadyPredictionHandoffStatus,
)


RISK_STATUS_MAP = {
    PredictionConvictionReviewStatus.READY_FOR_RISK: RiskReadyPredictionHandoffStatus.READY,
    PredictionConvictionReviewStatus.KEEP_FOR_MONITORING: RiskReadyPredictionHandoffStatus.WATCH,
    PredictionConvictionReviewStatus.IGNORE_NO_EDGE: RiskReadyPredictionHandoffStatus.BLOCKED,
    PredictionConvictionReviewStatus.IGNORE_LOW_CONFIDENCE: RiskReadyPredictionHandoffStatus.DEFERRED,
    PredictionConvictionReviewStatus.REQUIRE_MANUAL_PREDICTION_REVIEW: RiskReadyPredictionHandoffStatus.DEFERRED,
}


def build_risk_ready_handoff(*, review: PredictionConvictionReview) -> RiskReadyPredictionHandoff:
    handoff_status = RISK_STATUS_MAP[review.review_status]
    return RiskReadyPredictionHandoff.objects.create(
        linked_market=review.linked_intake_candidate.linked_market,
        linked_conviction_review=review,
        handoff_status=handoff_status,
        handoff_confidence=review.confidence,
        handoff_summary=f'Prediction-to-risk handoff status={handoff_status} generated from review {review.id}.',
        handoff_reason_codes=list(review.reason_codes or []),
        metadata={'review_status': review.review_status, 'conviction_bucket': review.conviction_bucket},
    )

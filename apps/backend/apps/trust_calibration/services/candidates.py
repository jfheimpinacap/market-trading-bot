from apps.trust_calibration.models import TrustCalibrationRecommendation


def build_policy_tuning_candidates(recommendations: list[TrustCalibrationRecommendation]) -> list[dict]:
    candidates = []
    for recommendation in recommendations:
        candidates.append(
            {
                'recommendation_id': recommendation.id,
                'action_type': recommendation.action_type,
                'current_trust_tier': recommendation.current_trust_tier,
                'recommended_trust_tier': recommendation.recommended_trust_tier,
                'recommendation_type': recommendation.recommendation_type,
                'reason_codes': recommendation.reason_codes,
                'confidence': str(recommendation.confidence),
                'apply_mode': 'MANUAL_APPROVAL_REQUIRED',
            }
        )
    return candidates

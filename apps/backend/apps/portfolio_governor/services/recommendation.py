from __future__ import annotations

from apps.portfolio_governor.models import PortfolioExposureDecision, PortfolioExposureRecommendation, PortfolioExposureRecommendationType


def create_exposure_recommendation(*, decision: PortfolioExposureDecision) -> PortfolioExposureRecommendation:
    recommendation_type = PortfolioExposureRecommendationType.KEEP_CURRENT_EXPOSURE
    blockers: list[str] = []

    mapping = {
        'THROTTLE_NEW_ENTRIES': PortfolioExposureRecommendationType.THROTTLE_CLUSTER_FOR_CONCENTRATION,
        'DEFER_PENDING_DISPATCH': PortfolioExposureRecommendationType.DEFER_WEAKER_PENDING_DISPATCH,
        'PARK_WEAKER_SESSION': PortfolioExposureRecommendationType.PARK_REDUNDANT_SESSION,
        'PAUSE_CLUSTER_ACTIVITY': PortfolioExposureRecommendationType.PAUSE_CLUSTER_FOR_PORTFOLIO_PRESSURE,
        'REQUIRE_MANUAL_EXPOSURE_REVIEW': PortfolioExposureRecommendationType.REQUIRE_MANUAL_EXPOSURE_REVIEW,
    }
    recommendation_type = mapping.get(decision.decision_type, PortfolioExposureRecommendationType.KEEP_CURRENT_EXPOSURE)

    if recommendation_type == PortfolioExposureRecommendationType.REQUIRE_MANUAL_EXPOSURE_REVIEW:
        blockers = ['directional_or_logic_conflict_ambiguous']

    return PortfolioExposureRecommendation.objects.create(
        recommendation_type=recommendation_type,
        target_cluster_snapshot=decision.linked_cluster_snapshot,
        target_conflict_review=decision.linked_conflict_review,
        target_exposure_decision=decision,
        rationale=decision.decision_summary,
        reason_codes=decision.reason_codes,
        confidence=0.72 if decision.auto_applicable else 0.55,
        blockers=blockers,
        metadata={'paper_only': True, 'local_first': True},
    )

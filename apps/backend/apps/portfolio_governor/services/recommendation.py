from __future__ import annotations

from apps.portfolio_governor.models import (
    PortfolioExposureApplyDecision,
    PortfolioExposureApplyRecommendation,
    PortfolioExposureApplyRecommendationType,
    PortfolioExposureApplyType,
    PortfolioExposureDecision,
    PortfolioExposureRecommendation,
    PortfolioExposureRecommendationType,
)


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


RECOMMENDATION_BY_APPLY_TYPE = {
    PortfolioExposureApplyType.APPLY_THROTTLE_NEW_ENTRIES: PortfolioExposureApplyRecommendationType.APPLY_CLUSTER_THROTTLE_NOW,
    PortfolioExposureApplyType.APPLY_DEFER_PENDING_DISPATCH: PortfolioExposureApplyRecommendationType.DEFER_PENDING_DISPATCH_SAFELY,
    PortfolioExposureApplyType.APPLY_PARK_SESSION: PortfolioExposureApplyRecommendationType.PARK_REDUNDANT_SESSION_NOW,
    PortfolioExposureApplyType.APPLY_PAUSE_CLUSTER_ACTIVITY: PortfolioExposureApplyRecommendationType.PAUSE_CLUSTER_ACTIVITY_CONSERVATIVELY,
    PortfolioExposureApplyType.APPLY_MANUAL_REVIEW_ONLY: PortfolioExposureApplyRecommendationType.REQUIRE_MANUAL_EXPOSURE_APPLY_REVIEW,
    PortfolioExposureApplyType.APPLY_NO_CHANGE: PortfolioExposureApplyRecommendationType.LEAVE_EXPOSURE_DECISION_AS_ADVISORY_ONLY,
}


def create_apply_recommendation(
    *,
    exposure_decision: PortfolioExposureDecision,
    apply_decision: PortfolioExposureApplyDecision,
) -> PortfolioExposureApplyRecommendation:
    recommendation_type = RECOMMENDATION_BY_APPLY_TYPE.get(
        apply_decision.apply_type,
        PortfolioExposureApplyRecommendationType.REQUIRE_MANUAL_EXPOSURE_APPLY_REVIEW,
    )
    blockers = []
    confidence = 0.75
    if apply_decision.apply_status in ['BLOCKED', 'FAILED']:
        blockers.append('apply_blocked')
        confidence = 0.45
    if not apply_decision.auto_applicable:
        blockers.append('manual_review_required')
        confidence = min(confidence, 0.5)

    return PortfolioExposureApplyRecommendation.objects.create(
        recommendation_type=recommendation_type,
        target_exposure_decision=exposure_decision,
        target_apply_decision=apply_decision,
        rationale=apply_decision.apply_summary,
        reason_codes=apply_decision.reason_codes,
        confidence=confidence,
        blockers=blockers,
        metadata={'paper_only': True, 'runtime_apply_bridge': True},
    )

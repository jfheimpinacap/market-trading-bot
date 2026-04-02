from __future__ import annotations

from apps.portfolio_governor.models import (
    PortfolioExposureConflictReview,
    PortfolioExposureDecision,
    PortfolioExposureDecisionStatus,
    PortfolioExposureDecisionType,
)


def derive_exposure_decision(*, review: PortfolioExposureConflictReview) -> PortfolioExposureDecision:
    decision_type = PortfolioExposureDecisionType.KEEP_EXPOSURE_AS_IS
    auto_applicable = True
    summary = 'Cluster exposure can remain as-is under current paper posture.'

    if review.review_type == 'PORTFOLIO_PRESSURE_CONFLICT':
        decision_type = PortfolioExposureDecisionType.PAUSE_CLUSTER_ACTIVITY
        summary = 'Pause additional cluster activity because global portfolio pressure is elevated.'
    elif review.review_type == 'DIRECTIONAL_CONFLICT':
        decision_type = PortfolioExposureDecisionType.REQUIRE_MANUAL_EXPOSURE_REVIEW
        auto_applicable = False
        summary = 'Directional conflict is ambiguous; require manual exposure review.'
    elif review.review_type == 'PENDING_DISPATCH_OVERLOAD':
        decision_type = PortfolioExposureDecisionType.DEFER_PENDING_DISPATCH
        summary = 'Defer weaker pending dispatches to avoid redundant concentration.'
    elif review.review_type == 'LOW_VALUE_CAPACITY_WASTE':
        decision_type = PortfolioExposureDecisionType.PARK_WEAKER_SESSION
        summary = 'Park weaker sessions to reduce low-value capacity pressure.'
    elif review.review_type == 'CONCENTRATION_RISK':
        decision_type = PortfolioExposureDecisionType.THROTTLE_NEW_ENTRIES
        summary = 'Throttle new entries for concentrated cluster risk.'

    if review.review_severity == 'CRITICAL' and review.review_type != 'DIRECTIONAL_CONFLICT':
        decision_type = PortfolioExposureDecisionType.PAUSE_CLUSTER_ACTIVITY
        summary = 'Critical cluster severity requires pausing new cluster activity.'

    return PortfolioExposureDecision.objects.create(
        linked_cluster_snapshot=review.linked_cluster_snapshot,
        linked_conflict_review=review,
        decision_type=decision_type,
        decision_status=PortfolioExposureDecisionStatus.PROPOSED,
        auto_applicable=auto_applicable,
        decision_summary=summary,
        reason_codes=[review.review_type.lower(), review.review_severity.lower()],
        metadata={'paper_only': True, 'no_forced_position_closure': True},
    )

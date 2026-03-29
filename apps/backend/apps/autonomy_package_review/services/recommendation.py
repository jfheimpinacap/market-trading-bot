from __future__ import annotations

from apps.autonomy_package_review.models import PackageResolution, PackageResolutionStatus, PackageReviewRecommendationType


def build_package_review_recommendations(*, resolution: PackageResolution, pending_count: int) -> list[dict]:
    rows: list[dict] = []

    if resolution.resolution_status == PackageResolutionStatus.BLOCKED:
        rows.append(
            {
                'recommendation_type': PackageReviewRecommendationType.REQUIRE_MANUAL_PACKAGE_REVIEW,
                'rationale': 'Package is blocked and requires manual intervention before further resolution actions.',
                'reason_codes': ['package_blocked'],
                'confidence': '0.9000',
                'blockers': list(resolution.blockers or ['package_blocked']),
                'metadata': {'status': resolution.resolution_status},
            }
        )
        return rows

    if resolution.resolution_status == PackageResolutionStatus.PENDING:
        rows.append(
            {
                'recommendation_type': PackageReviewRecommendationType.ACKNOWLEDGE_PACKAGE,
                'rationale': 'Package is registered and should be acknowledged to confirm manual review ownership.',
                'reason_codes': ['pending_acknowledgement'],
                'confidence': '0.7800',
                'blockers': list(resolution.blockers or []),
                'metadata': {'status': resolution.resolution_status},
            }
        )
        rows.append(
            {
                'recommendation_type': PackageReviewRecommendationType.KEEP_PACKAGE_PENDING,
                'rationale': 'Keep package pending until roadmap/scenario/program/manager owners evaluate downstream adoption.',
                'reason_codes': ['awaiting_owner_review'],
                'confidence': '0.6200',
                'blockers': list(resolution.blockers or []),
                'metadata': {'status': resolution.resolution_status},
            }
        )

    if resolution.resolution_status == PackageResolutionStatus.ACKNOWLEDGED:
        rows.append(
            {
                'recommendation_type': PackageReviewRecommendationType.MARK_PACKAGE_ADOPTED,
                'rationale': 'Package is already acknowledged and can be marked adopted once downstream owner confirms intent.',
                'reason_codes': ['eligible_for_adoption'],
                'confidence': '0.7600',
                'blockers': list(resolution.blockers or []),
                'metadata': {'status': resolution.resolution_status},
            }
        )

    if resolution.resolution_status in {PackageResolutionStatus.DEFERRED, PackageResolutionStatus.REJECTED}:
        rows.append(
            {
                'recommendation_type': PackageReviewRecommendationType.REQUIRE_MANUAL_PACKAGE_REVIEW,
                'rationale': 'Deferred/rejected packages must retain explicit rationale and may require follow-up review.',
                'reason_codes': ['resolution_not_adopted'],
                'confidence': '0.7200',
                'blockers': list(resolution.blockers or []),
                'metadata': {'status': resolution.resolution_status},
            }
        )

    if pending_count >= 2:
        rows.append(
            {
                'recommendation_type': PackageReviewRecommendationType.REORDER_PACKAGE_REVIEW_PRIORITY,
                'rationale': 'Multiple pending packages were detected; review priority should be explicitly reordered.',
                'reason_codes': ['multi_pending_packages'],
                'confidence': '0.6500',
                'blockers': [],
                'metadata': {'pending_count': pending_count},
            }
        )

    return rows

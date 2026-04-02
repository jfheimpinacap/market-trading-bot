from __future__ import annotations

from apps.portfolio_governor.models import (
    PortfolioExposureClusterSnapshot,
    PortfolioExposureConcentrationStatus,
    PortfolioExposureConflictReview,
    PortfolioExposureConflictReviewSeverity,
    PortfolioExposureConflictReviewType,
)


def review_cluster_conflicts(*, cluster: PortfolioExposureClusterSnapshot) -> list[PortfolioExposureConflictReview]:
    reviews: list[PortfolioExposureConflictReview] = []

    if cluster.concentration_status in {
        PortfolioExposureConcentrationStatus.ELEVATED,
        PortfolioExposureConcentrationStatus.HIGH,
        PortfolioExposureConcentrationStatus.CRITICAL,
    }:
        severity = PortfolioExposureConflictReviewSeverity.CAUTION
        if cluster.concentration_status == PortfolioExposureConcentrationStatus.HIGH:
            severity = PortfolioExposureConflictReviewSeverity.HIGH
        if cluster.concentration_status == PortfolioExposureConcentrationStatus.CRITICAL:
            severity = PortfolioExposureConflictReviewSeverity.CRITICAL
        reviews.append(
            PortfolioExposureConflictReview.objects.create(
                linked_cluster_snapshot=cluster,
                review_type=PortfolioExposureConflictReviewType.CONCENTRATION_RISK,
                review_severity=severity,
                review_summary='Cluster concentration pressure is elevated across sessions, positions, or pending dispatches.',
                reason_codes=['cluster_concentration', cluster.concentration_status.lower()],
                metadata={'session_count': cluster.session_count, 'pending_dispatch_count': cluster.pending_dispatch_count},
            )
        )

    if cluster.pending_dispatch_count >= 2:
        reviews.append(
            PortfolioExposureConflictReview.objects.create(
                linked_cluster_snapshot=cluster,
                review_type=PortfolioExposureConflictReviewType.PENDING_DISPATCH_OVERLOAD,
                review_severity=PortfolioExposureConflictReviewSeverity.HIGH if cluster.pending_dispatch_count >= 3 else PortfolioExposureConflictReviewSeverity.CAUTION,
                review_summary='Pending dispatches are stacking on the same exposure cluster.',
                reason_codes=['pending_dispatch_overload'],
                metadata={'pending_dispatch_count': cluster.pending_dispatch_count},
            )
        )

    if cluster.net_direction == 'MIXED' and cluster.session_count >= 2:
        reviews.append(
            PortfolioExposureConflictReview.objects.create(
                linked_cluster_snapshot=cluster,
                review_type=PortfolioExposureConflictReviewType.DIRECTIONAL_CONFLICT,
                review_severity=PortfolioExposureConflictReviewSeverity.HIGH,
                review_summary='Directional conflict detected inside the same cluster context.',
                reason_codes=['directional_conflict'],
                metadata={'net_direction': cluster.net_direction},
            )
        )

    low_value_count = cluster.session_contributions.filter(contribution_role='LOW_VALUE').count()
    redundant_count = cluster.session_contributions.filter(contribution_role='REDUNDANT').count()
    if low_value_count + redundant_count >= 2:
        reviews.append(
            PortfolioExposureConflictReview.objects.create(
                linked_cluster_snapshot=cluster,
                review_type=PortfolioExposureConflictReviewType.LOW_VALUE_CAPACITY_WASTE,
                review_severity=PortfolioExposureConflictReviewSeverity.CAUTION,
                review_summary='Low-value or redundant sessions are consuming global portfolio capacity.',
                reason_codes=['redundant_low_value_stacking'],
                metadata={'low_value_count': low_value_count, 'redundant_count': redundant_count},
            )
        )

    if cluster.aggregate_risk_pressure_state in {'THROTTLED', 'BLOCK_NEW_EXPOSURE'} and cluster.concentration_status in {'HIGH', 'CRITICAL'}:
        reviews.append(
            PortfolioExposureConflictReview.objects.create(
                linked_cluster_snapshot=cluster,
                review_type=PortfolioExposureConflictReviewType.PORTFOLIO_PRESSURE_CONFLICT,
                review_severity=PortfolioExposureConflictReviewSeverity.CRITICAL if cluster.aggregate_risk_pressure_state == 'BLOCK_NEW_EXPOSURE' else PortfolioExposureConflictReviewSeverity.HIGH,
                review_summary='Portfolio posture and cluster pressure conflict with additional exposure.',
                reason_codes=['portfolio_pressure_conflict', cluster.aggregate_risk_pressure_state.lower()],
                metadata={'aggregate_risk_pressure_state': cluster.aggregate_risk_pressure_state},
            )
        )

    if not reviews:
        reviews.append(
            PortfolioExposureConflictReview.objects.create(
                linked_cluster_snapshot=cluster,
                review_type=PortfolioExposureConflictReviewType.REDUNDANT_SESSION_STACKING,
                review_severity=PortfolioExposureConflictReviewSeverity.INFO,
                review_summary='No material concentration/conflict risk detected for this cluster.',
                reason_codes=['healthy_cluster'],
                metadata={'cluster_status': 'healthy'},
            )
        )

    return reviews

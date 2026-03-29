from __future__ import annotations

from dataclasses import dataclass

from apps.autonomy_package.models import GovernancePackage, GovernancePackageStatus, GovernancePackageTargetScope
from apps.autonomy_package_review.models import PackageResolution, PackageResolutionStatus, PackageResolutionType

TYPE_BY_SCOPE = {
    GovernancePackageTargetScope.ROADMAP: PackageResolutionType.ROADMAP_PACKAGE_ACKNOWLEDGED,
    GovernancePackageTargetScope.SCENARIO: PackageResolutionType.SCENARIO_PACKAGE_ACKNOWLEDGED,
    GovernancePackageTargetScope.PROGRAM: PackageResolutionType.PROGRAM_PACKAGE_ACKNOWLEDGED,
    GovernancePackageTargetScope.MANAGER: PackageResolutionType.MANAGER_PACKAGE_ACKNOWLEDGED,
    GovernancePackageTargetScope.OPERATOR_REVIEW: PackageResolutionType.OPERATOR_PACKAGE_ACKNOWLEDGED,
}


@dataclass
class PackageResolutionEvaluation:
    downstream_status: str
    ready_for_resolution: bool
    blockers: list[str]
    reason_codes: list[str]
    resolution_status: str
    resolution_type: str
    rationale: str


def evaluate_package_resolution(package: GovernancePackage, existing: PackageResolution | None = None) -> PackageResolutionEvaluation:
    if existing is not None:
        return PackageResolutionEvaluation(
            downstream_status=existing.resolution_status,
            ready_for_resolution=existing.resolution_status not in {PackageResolutionStatus.CLOSED, PackageResolutionStatus.ADOPTED},
            blockers=list(existing.blockers or []),
            reason_codes=list(existing.reason_codes or []),
            resolution_status=existing.resolution_status,
            resolution_type=existing.resolution_type,
            rationale=existing.rationale,
        )

    if package.package_status == GovernancePackageStatus.BLOCKED:
        blockers = list(package.blockers or ['package_blocked'])
        return PackageResolutionEvaluation(
            downstream_status=PackageResolutionStatus.BLOCKED,
            ready_for_resolution=False,
            blockers=blockers,
            reason_codes=['package_blocked'],
            resolution_status=PackageResolutionStatus.BLOCKED,
            resolution_type=PackageResolutionType.MANUAL_REVIEW_REQUIRED,
            rationale='Governance package is blocked and requires manual review before acknowledgment or adoption.',
        )

    if package.package_status not in {
        GovernancePackageStatus.REGISTERED,
        GovernancePackageStatus.READY,
        GovernancePackageStatus.ACKNOWLEDGED,
    }:
        return PackageResolutionEvaluation(
            downstream_status='UNKNOWN',
            ready_for_resolution=False,
            blockers=['package_not_registered_or_ready'],
            reason_codes=['package_not_registered_or_ready'],
            resolution_status=PackageResolutionStatus.PENDING,
            resolution_type=PackageResolutionType.MANUAL_REVIEW_REQUIRED,
            rationale='Only ready/registered/acknowledged governance packages are eligible for downstream review tracking.',
        )

    status = PackageResolutionStatus.ACKNOWLEDGED if package.package_status == GovernancePackageStatus.ACKNOWLEDGED else PackageResolutionStatus.PENDING
    return PackageResolutionEvaluation(
        downstream_status=status,
        ready_for_resolution=True,
        blockers=[],
        reason_codes=['package_acknowledged_in_registry'] if status == PackageResolutionStatus.ACKNOWLEDGED else ['awaiting_manual_package_review'],
        resolution_status=status,
        resolution_type=TYPE_BY_SCOPE.get(package.target_scope, PackageResolutionType.MANUAL_REVIEW_REQUIRED),
        rationale=(
            'Governance package has been acknowledged in package registry and awaits manual adopt/defer/reject action.'
            if status == PackageResolutionStatus.ACKNOWLEDGED
            else 'Governance package is registered and awaiting manual acknowledge/adopt/defer/reject review.'
        ),
    )

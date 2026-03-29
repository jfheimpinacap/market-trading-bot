from __future__ import annotations

from dataclasses import dataclass

from apps.autonomy_package.models import GovernancePackage, GovernancePackageStatus
from apps.autonomy_package_review.models import PackageResolution
from apps.autonomy_package_review.services.status import evaluate_package_resolution


@dataclass
class PackageReviewCandidate:
    governance_package: int
    linked_decisions: list[int]
    target_scope: str
    package_status: str
    downstream_status: str
    ready_for_resolution: bool
    blockers: list[str]
    metadata: dict


def build_package_review_candidates() -> list[PackageReviewCandidate]:
    rows: list[PackageReviewCandidate] = []
    packages = GovernancePackage.objects.prefetch_related('linked_decisions').filter(
        package_status__in=[
            GovernancePackageStatus.READY,
            GovernancePackageStatus.REGISTERED,
            GovernancePackageStatus.ACKNOWLEDGED,
            GovernancePackageStatus.BLOCKED,
        ]
    ).order_by('-updated_at', '-id')

    for package in packages:
        existing = PackageResolution.objects.filter(governance_package=package).first()
        evaluation = evaluate_package_resolution(package, existing)
        rows.append(
            PackageReviewCandidate(
                governance_package=package.id,
                linked_decisions=list(package.linked_decisions.values_list('id', flat=True)),
                target_scope=package.target_scope,
                package_status=package.package_status,
                downstream_status=evaluation.downstream_status,
                ready_for_resolution=evaluation.ready_for_resolution,
                blockers=evaluation.blockers,
                metadata={
                    'title': package.title,
                    'summary': package.summary,
                    'priority_level': package.priority_level,
                    'grouping_key': package.grouping_key,
                    'linked_target_artifact': package.linked_target_artifact,
                },
            )
        )
    return rows

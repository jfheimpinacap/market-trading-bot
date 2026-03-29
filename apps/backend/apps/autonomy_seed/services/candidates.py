from __future__ import annotations

from dataclasses import dataclass

from apps.autonomy_package.models import GovernancePackageTargetScope
from apps.autonomy_package_review.models import PackageResolution, PackageResolutionStatus
from apps.autonomy_seed.services.dedup import find_duplicate_seed


@dataclass
class SeedCandidate:
    governance_package: int
    package_resolution: int
    linked_decisions: list[int]
    target_scope: str
    priority_level: str
    ready_for_seed: bool
    existing_seed: int | None
    blockers: list[str]
    metadata: dict


def build_seed_candidates() -> list[SeedCandidate]:
    rows: list[SeedCandidate] = []
    resolutions = PackageResolution.objects.select_related('governance_package').prefetch_related('governance_package__linked_decisions').filter(
        resolution_status=PackageResolutionStatus.ADOPTED
    ).order_by('-updated_at', '-id')[:500]

    for resolution in resolutions:
        package = resolution.governance_package
        duplicate = find_duplicate_seed(governance_package_id=package.id, target_scope=package.target_scope)

        blockers = list(resolution.blockers or []) + list(package.blockers or [])
        if package.target_scope not in GovernancePackageTargetScope.values:
            blockers.append('unsupported_target_scope')
        if not package.title:
            blockers.append('missing_package_title')
        if not package.summary:
            blockers.append('missing_package_summary')

        rows.append(
            SeedCandidate(
                governance_package=package.id,
                package_resolution=resolution.id,
                linked_decisions=list(package.linked_decisions.values_list('id', flat=True)),
                target_scope=package.target_scope,
                priority_level=package.priority_level,
                ready_for_seed=not blockers and duplicate is None,
                existing_seed=duplicate.id if duplicate else None,
                blockers=blockers,
                metadata={
                    'package_status': package.package_status,
                    'resolution_status': resolution.resolution_status,
                    'campaign_id': package.linked_decisions.first().campaign_id if package.linked_decisions.exists() else None,
                },
            )
        )

    return rows

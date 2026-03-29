from __future__ import annotations

from django.utils import timezone

from apps.autonomy_package.models import GovernancePackage, GovernancePackageStatus
from apps.autonomy_package_review.models import PackageResolution, PackageResolutionStatus
from apps.autonomy_package_review.services.status import TYPE_BY_SCOPE


def _default_rationale(status: str) -> str:
    return {
        PackageResolutionStatus.ACKNOWLEDGED: 'Package acknowledged by operator for manual downstream review tracking.',
        PackageResolutionStatus.ADOPTED: 'Package adopted as future-cycle input artifact by manual governance decision.',
        PackageResolutionStatus.DEFERRED: 'Package deferred pending additional governance context or scheduling capacity.',
        PackageResolutionStatus.REJECTED: 'Package rejected after manual governance review due to insufficient fit or evidence.',
    }.get(status, 'Manual package resolution update recorded.')


def set_package_resolution(
    *,
    package: GovernancePackage,
    resolution_status: str,
    actor: str,
    rationale: str = '',
    reason_codes: list[str] | None = None,
) -> PackageResolution:
    reason_codes = reason_codes or []
    resolution, _ = PackageResolution.objects.get_or_create(
        governance_package=package,
        defaults={
            'resolution_status': resolution_status,
            'resolution_type': TYPE_BY_SCOPE.get(package.target_scope, 'MANUAL_REVIEW_REQUIRED'),
            'rationale': rationale or _default_rationale(resolution_status),
            'reason_codes': reason_codes,
            'blockers': [],
            'linked_target_artifact': package.linked_target_artifact,
            'metadata': {'source': 'manual_action'},
        },
    )

    resolution.resolution_status = resolution_status
    resolution.resolution_type = TYPE_BY_SCOPE.get(package.target_scope, 'MANUAL_REVIEW_REQUIRED')
    resolution.rationale = rationale or _default_rationale(resolution_status)
    resolution.reason_codes = reason_codes
    resolution.blockers = []
    resolution.linked_target_artifact = package.linked_target_artifact
    resolution.resolved_by = actor
    resolution.resolved_at = timezone.now()
    resolution.metadata = {**(resolution.metadata or {}), 'source': 'manual_action', 'actor': actor}

    if resolution_status == PackageResolutionStatus.ADOPTED:
        package.package_status = GovernancePackageStatus.ACKNOWLEDGED
        package.metadata = {**(package.metadata or {}), 'adopted_in_package_review': True, 'adopted_at': timezone.now().isoformat()}
        package.save(update_fields=['package_status', 'metadata', 'updated_at'])

    resolution.save()
    return resolution


def acknowledge_package(*, package: GovernancePackage, actor: str, rationale: str = '', reason_codes: list[str] | None = None) -> PackageResolution:
    package.package_status = GovernancePackageStatus.ACKNOWLEDGED
    package.metadata = {**(package.metadata or {}), 'acknowledged_in_package_review': True, 'acknowledged_by': actor}
    package.save(update_fields=['package_status', 'metadata', 'updated_at'])
    return set_package_resolution(package=package, resolution_status=PackageResolutionStatus.ACKNOWLEDGED, actor=actor, rationale=rationale, reason_codes=reason_codes)


def adopt_package(*, package: GovernancePackage, actor: str, rationale: str = '', reason_codes: list[str] | None = None) -> PackageResolution:
    return set_package_resolution(package=package, resolution_status=PackageResolutionStatus.ADOPTED, actor=actor, rationale=rationale, reason_codes=reason_codes)


def defer_package(*, package: GovernancePackage, actor: str, rationale: str = '', reason_codes: list[str] | None = None) -> PackageResolution:
    return set_package_resolution(package=package, resolution_status=PackageResolutionStatus.DEFERRED, actor=actor, rationale=rationale, reason_codes=reason_codes)


def reject_package(*, package: GovernancePackage, actor: str, rationale: str = '', reason_codes: list[str] | None = None) -> PackageResolution:
    return set_package_resolution(package=package, resolution_status=PackageResolutionStatus.REJECTED, actor=actor, rationale=rationale, reason_codes=reason_codes)

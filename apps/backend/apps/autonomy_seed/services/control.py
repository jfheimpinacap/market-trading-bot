from django.core.exceptions import ValidationError

from apps.autonomy_package_review.models import PackageResolution, PackageResolutionStatus
from apps.autonomy_seed.models import GovernanceSeedStatus
from apps.autonomy_seed.services.dedup import find_duplicate_seed
from apps.autonomy_seed.services.registration import create_registered_seed


def register_seed_for_package(*, package_id: int, actor: str = 'operator-ui'):
    try:
        resolution = PackageResolution.objects.select_related('governance_package').prefetch_related('governance_package__linked_decisions').get(
            governance_package_id=package_id
        )
    except PackageResolution.DoesNotExist as exc:
        raise ValidationError('Package resolution is required before seed registration.') from exc

    package = resolution.governance_package
    if resolution.resolution_status != PackageResolutionStatus.ADOPTED:
        raise ValidationError('Governance package must be ADOPTED before seed registration.')

    blockers = list(resolution.blockers or []) + list(package.blockers or [])
    if blockers:
        raise ValidationError('Governance package still has blockers and requires manual seed review.')

    duplicate = find_duplicate_seed(governance_package_id=package.id, target_scope=package.target_scope)
    if duplicate:
        duplicate.seed_status = GovernanceSeedStatus.DUPLICATE_SKIPPED
        duplicate.metadata = {**(duplicate.metadata or {}), 'duplicate_skip_checked': True}
        duplicate.save(update_fields=['seed_status', 'metadata', 'updated_at'])
        return duplicate

    return create_registered_seed(
        candidate={
            'governance_package': package.id,
            'package_resolution': resolution.id,
            'linked_decisions': list(package.linked_decisions.values_list('id', flat=True)),
            'target_scope': package.target_scope,
            'priority_level': package.priority_level,
            'blockers': blockers,
            'metadata': {
                'package_status': package.package_status,
                'resolution_status': resolution.resolution_status,
            },
        },
        actor=actor,
    )

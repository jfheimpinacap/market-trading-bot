from apps.autonomy_seed.models import GovernanceSeed


def find_duplicate_seed(*, governance_package_id: int, target_scope: str) -> GovernanceSeed | None:
    return GovernanceSeed.objects.filter(
        governance_package_id=governance_package_id,
        target_scope=target_scope,
        seed_status__in=['REGISTERED', 'ACKNOWLEDGED', 'READY', 'DUPLICATE_SKIPPED'],
    ).first()

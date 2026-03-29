from apps.autonomy_package.models import GovernancePackage


def find_duplicate_package(*, grouping_key: str, target_scope: str) -> GovernancePackage | None:
    return GovernancePackage.objects.filter(
        grouping_key=grouping_key,
        target_scope=target_scope,
        package_status__in=['REGISTERED', 'ACKNOWLEDGED', 'READY'],
    ).first()

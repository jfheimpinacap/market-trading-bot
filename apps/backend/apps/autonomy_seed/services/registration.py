from django.utils import timezone

from apps.autonomy_seed.models import GovernanceSeed, GovernanceSeedStatus, GovernanceSeedType

SEED_TYPE_BY_SCOPE = {
    'roadmap': GovernanceSeedType.ROADMAP_SEED,
    'scenario': GovernanceSeedType.SCENARIO_SEED,
    'program': GovernanceSeedType.PROGRAM_SEED,
    'manager': GovernanceSeedType.MANAGER_SEED,
    'operator_review': GovernanceSeedType.OPERATOR_REVIEW_SEED,
}


def create_registered_seed(*, candidate: dict, actor: str = 'operator-ui') -> GovernanceSeed:
    seed_type = SEED_TYPE_BY_SCOPE.get(candidate['target_scope'], GovernanceSeedType.OPERATOR_REVIEW_SEED)
    return GovernanceSeed.objects.create(
        governance_package_id=candidate['governance_package'],
        package_resolution_id=candidate['package_resolution'],
        seed_type=seed_type,
        seed_status=GovernanceSeedStatus.REGISTERED,
        target_scope=candidate['target_scope'],
        priority_level=candidate['priority_level'],
        title=f"{candidate['target_scope'].upper()} seed · package #{candidate['governance_package']}",
        summary='Reusable planning seed from ADOPTED governance package for next-cycle manual-first intake.',
        rationale='Derived from package review adoption without auto-applying into destination modules.',
        linked_packages=[candidate['governance_package']],
        linked_decisions=list(candidate['linked_decisions']),
        reason_codes=['package_adopted_seed_registered'],
        blockers=list(candidate.get('blockers') or []),
        grouping_key=f"{candidate['target_scope']}:{candidate['governance_package']}",
        registered_by=actor,
        registered_at=timezone.now(),
        linked_target_artifact='',
        metadata={**(candidate.get('metadata') or {}), 'source': 'autonomy_seed'},
    )

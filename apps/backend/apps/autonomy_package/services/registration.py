from django.utils import timezone

from apps.autonomy_decision.models import GovernanceDecisionType
from apps.autonomy_package.models import GovernancePackage, GovernancePackageStatus, GovernancePackageType

PACKAGE_BY_DECISION_TYPE = {
    GovernanceDecisionType.ROADMAP_DECISION_PACKAGE: GovernancePackageType.ROADMAP_CHANGE_PACKAGE,
    GovernanceDecisionType.SCENARIO_DECISION_PACKAGE: GovernancePackageType.SCENARIO_CAUTION_PACKAGE,
    GovernanceDecisionType.PROGRAM_DECISION_PACKAGE: GovernancePackageType.PROGRAM_GOVERNANCE_PACKAGE,
    GovernanceDecisionType.MANAGER_DECISION_NOTE: GovernancePackageType.MANAGER_REVIEW_PACKAGE,
    GovernanceDecisionType.OPERATOR_DECISION_NOTE: GovernancePackageType.OPERATOR_REVIEW_PACKAGE,
}


def create_registered_package(*, candidate: dict, actor: str = 'operator-ui') -> GovernancePackage:
    package = GovernancePackage.objects.create(
        package_type=PACKAGE_BY_DECISION_TYPE.get(candidate['decision_type'], GovernancePackageType.OPERATOR_REVIEW_PACKAGE),
        package_status=GovernancePackageStatus.REGISTERED,
        target_scope=candidate['target_scope'],
        priority_level=candidate['priority_level'],
        title=f"{candidate['target_scope'].upper()} package seed · decision #{candidate['governance_decision']}",
        summary='Reusable, auditable decision bundle for the next planning cycle; no automatic apply performed.',
        rationale='Derived from already registered governance decision(s) to produce explicit planning seeds.',
        decision_count=1,
        reason_codes=['decision_registered_for_packaging'],
        blockers=list(candidate['blockers'] or []),
        grouping_key=candidate['grouping_key'],
        registered_by=actor,
        registered_at=timezone.now(),
        linked_target_artifact='',
        metadata={**(candidate.get('metadata') or {}), 'source': 'autonomy_package'},
    )
    package.linked_decisions.add(candidate['governance_decision'])
    return package

from django.core.exceptions import ValidationError

from apps.autonomy_decision.models import GovernanceDecision, GovernanceDecisionStatus
from apps.autonomy_package.models import GovernancePackage, GovernancePackageStatus
from apps.autonomy_package.services.dedup import find_duplicate_package
from apps.autonomy_package.services.registration import create_registered_package


def register_package_for_decision(*, decision_id: int, actor: str = 'operator-ui') -> GovernancePackage:
    decision = GovernanceDecision.objects.select_related('planning_proposal', 'campaign').get(pk=decision_id)

    if decision.decision_status not in [GovernanceDecisionStatus.REGISTERED, GovernanceDecisionStatus.ACKNOWLEDGED]:
        raise ValidationError('Governance decision must be REGISTERED or ACKNOWLEDGED before package registration.')
    if decision.blockers:
        raise ValidationError('Governance decision still has blockers and requires manual package review.')

    proposal_type = decision.planning_proposal.proposal_type if decision.planning_proposal else 'cross'
    grouping_key = f"{decision.target_scope}:{proposal_type}:{decision.priority_level}"
    duplicate = find_duplicate_package(grouping_key=grouping_key, target_scope=decision.target_scope)

    if duplicate:
        duplicate.package_status = GovernancePackageStatus.DUPLICATE_SKIPPED
        duplicate.metadata = {**(duplicate.metadata or {}), 'duplicate_skip_checked': True}
        duplicate.save(update_fields=['package_status', 'metadata', 'updated_at'])
        return duplicate

    return create_registered_package(
        candidate={
            'governance_decision': decision.id,
            'decision_type': decision.decision_type,
            'target_scope': decision.target_scope,
            'priority_level': decision.priority_level,
            'grouping_key': grouping_key,
            'blockers': decision.blockers,
            'metadata': {'decision_status': decision.decision_status, 'campaign_title': decision.campaign.title if decision.campaign else None},
        },
        actor=actor,
    )

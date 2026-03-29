from django.core.exceptions import ValidationError

from apps.autonomy_decision.models import GovernanceDecision, GovernanceDecisionStatus
from apps.autonomy_decision.services.dedup import find_duplicate_decision
from apps.autonomy_decision.services.registration import create_registered_decision
from apps.autonomy_decision.services.status import TARGET_BY_PROPOSAL_TYPE
from apps.autonomy_planning_review.models import PlanningProposalResolution, PlanningProposalResolutionStatus


def register_decision_for_proposal(*, proposal_id: int, actor: str = 'operator-ui') -> GovernanceDecision:
    resolution = PlanningProposalResolution.objects.select_related('planning_proposal', 'campaign').get(planning_proposal_id=proposal_id)
    if resolution.resolution_status != PlanningProposalResolutionStatus.ACCEPTED:
        raise ValidationError('Planning proposal must be ACCEPTED before decision registration.')

    proposal = resolution.planning_proposal
    target_scope = TARGET_BY_PROPOSAL_TYPE.get(proposal.proposal_type, proposal.target_scope)
    duplicate = find_duplicate_decision(proposal_id=proposal.id, target_scope=target_scope)
    if duplicate:
        duplicate.decision_status = GovernanceDecisionStatus.DUPLICATE_SKIPPED
        duplicate.metadata = {**(duplicate.metadata or {}), 'duplicate_skip_checked': True}
        duplicate.save(update_fields=['decision_status', 'metadata', 'updated_at'])
        return duplicate

    if resolution.blockers:
        raise ValidationError('Accepted planning proposal still has blockers and requires manual decision review.')

    return create_registered_decision(resolution=resolution, actor=actor)


def acknowledge_decision(*, decision_id: int) -> GovernanceDecision:
    decision = GovernanceDecision.objects.get(pk=decision_id)
    decision.decision_status = GovernanceDecisionStatus.ACKNOWLEDGED
    decision.metadata = {**(decision.metadata or {}), 'acknowledged': True}
    decision.save(update_fields=['decision_status', 'metadata', 'updated_at'])
    return decision

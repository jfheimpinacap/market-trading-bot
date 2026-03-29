from __future__ import annotations

from django.utils import timezone

from apps.autonomy_backlog.models import GovernanceBacklogItem
from apps.autonomy_intake.models import PlanningProposal, PlanningProposalStatus
from apps.autonomy_intake.services.dedup import find_duplicate_proposal
from apps.autonomy_intake.services.emission import emit_planning_proposal
from apps.autonomy_intake.services.recommendation import proposal_type_for_backlog_type, target_scope_for_proposal_type


def emit_proposal_for_backlog_item(*, backlog_item_id: int, actor: str = 'operator-ui') -> PlanningProposal:
    item = GovernanceBacklogItem.objects.get(pk=backlog_item_id)
    if item.backlog_status not in {'READY', 'PRIORITIZED'}:
        raise ValueError('Backlog item must be READY or PRIORITIZED before proposal emission.')

    proposal_type = proposal_type_for_backlog_type(item.backlog_type)
    if not proposal_type:
        raise ValueError('Backlog item type is not supported for planning proposal conversion.')

    duplicate = find_duplicate_proposal(backlog_item_id=item.id, target_scope=target_scope_for_proposal_type(proposal_type))
    if duplicate:
        if duplicate.proposal_status != PlanningProposalStatus.DUPLICATE_SKIPPED:
            duplicate.metadata = {**(duplicate.metadata or {}), 'duplicate_checked_at': timezone.now().isoformat(), 'manual_actor': actor}
            duplicate.save(update_fields=['metadata', 'updated_at'])
        return duplicate

    return emit_planning_proposal(backlog_item=item, actor=actor)


def acknowledge_proposal(*, proposal_id: int, actor: str = 'operator-ui') -> PlanningProposal:
    proposal = PlanningProposal.objects.get(pk=proposal_id)
    proposal.proposal_status = PlanningProposalStatus.ACKNOWLEDGED
    proposal.metadata = {**(proposal.metadata or {}), 'acknowledged_by': actor, 'acknowledged_at': timezone.now().isoformat()}
    proposal.save(update_fields=['proposal_status', 'metadata', 'updated_at'])
    return proposal

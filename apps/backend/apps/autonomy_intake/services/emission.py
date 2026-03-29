from __future__ import annotations

from django.utils import timezone

from apps.autonomy_backlog.models import GovernanceBacklogItem
from apps.autonomy_intake.models import PlanningProposal, PlanningProposalStatus
from apps.autonomy_intake.services.recommendation import proposal_type_for_backlog_type, target_scope_for_proposal_type


def emit_planning_proposal(*, backlog_item: GovernanceBacklogItem, actor: str = 'operator-ui') -> PlanningProposal:
    proposal_type = proposal_type_for_backlog_type(backlog_item.backlog_type)
    if not proposal_type:
        raise ValueError('Backlog type is not supported for autonomy intake proposal emission.')

    return PlanningProposal.objects.create(
        backlog_item=backlog_item,
        advisory_artifact=backlog_item.advisory_artifact,
        insight=backlog_item.insight,
        campaign=backlog_item.campaign,
        proposal_type=proposal_type,
        proposal_status=PlanningProposalStatus.EMITTED,
        target_scope=target_scope_for_proposal_type(proposal_type),
        priority_level=backlog_item.priority_level,
        summary=backlog_item.summary,
        rationale=backlog_item.rationale,
        reason_codes=sorted({*(backlog_item.reason_codes or []), 'manual_intake_emission'}),
        blockers=list(backlog_item.blockers or []),
        emitted_by=actor,
        emitted_at=timezone.now(),
        linked_target_artifact='',
        metadata={
            'source_backlog_item_id': backlog_item.id,
            'source_backlog_type': backlog_item.backlog_type,
            'manual_first': True,
            'auto_apply': False,
        },
    )

from __future__ import annotations

from apps.autonomy_intake.models import PlanningProposal


DUPLICATE_STATUSES = {'PENDING_REVIEW', 'READY', 'EMITTED', 'ACKNOWLEDGED'}


def find_duplicate_proposal(*, backlog_item_id: int, target_scope: str) -> PlanningProposal | None:
    return PlanningProposal.objects.filter(
        backlog_item_id=backlog_item_id,
        target_scope=target_scope,
        proposal_status__in=DUPLICATE_STATUSES,
    ).order_by('-updated_at', '-id').first()

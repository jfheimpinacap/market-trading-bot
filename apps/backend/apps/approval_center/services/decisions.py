from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.approval_center.models import ApprovalDecision, ApprovalDecisionType, ApprovalRequest, ApprovalRequestStatus, ApprovalSourceType
from apps.go_live_gate.models import GoLiveApprovalRequest, GoLiveApprovalStatus
from apps.operator_queue.models import OperatorDecisionType, OperatorQueueItem, OperatorQueueStatus
from apps.operator_queue.services.decisions import approve_queue_item, reject_queue_item
from apps.runbook_engine.models import RunbookApprovalCheckpoint, RunbookApprovalCheckpointStatus
from apps.runbook_engine.services import continue_autopilot


STATUS_BY_DECISION = {
    ApprovalDecisionType.APPROVE: ApprovalRequestStatus.APPROVED,
    ApprovalDecisionType.REJECT: ApprovalRequestStatus.REJECTED,
    ApprovalDecisionType.EXPIRE: ApprovalRequestStatus.EXPIRED,
    ApprovalDecisionType.ESCALATE: ApprovalRequestStatus.ESCALATED,
}


@transaction.atomic
def apply_decision(*, approval: ApprovalRequest, decision: str, rationale: str = '', decided_by: str = 'local-operator', metadata: dict | None = None) -> ApprovalRequest:
    decision_code = decision.upper()
    if decision_code not in ApprovalDecisionType.values:
        raise ValueError(f'Unsupported decision: {decision}.')
    if approval.status != ApprovalRequestStatus.PENDING and decision_code != ApprovalDecisionType.ESCALATE:
        raise ValueError('Only pending approvals can be resolved.')

    if approval.source_type == ApprovalSourceType.RUNBOOK_CHECKPOINT:
        _apply_runbook_checkpoint_decision(approval=approval, decision=decision_code, reviewer=decided_by)
    elif approval.source_type == ApprovalSourceType.GO_LIVE_REQUEST:
        _apply_go_live_decision(approval=approval, decision=decision_code)
    elif approval.source_type == ApprovalSourceType.OPERATOR_QUEUE_ITEM:
        _apply_operator_queue_decision(approval=approval, decision=decision_code, rationale=rationale, decided_by=decided_by)

    approval.status = STATUS_BY_DECISION[decision_code]
    approval.decided_at = timezone.now()
    approval.save(update_fields=['status', 'decided_at', 'updated_at'])

    ApprovalDecision.objects.create(
        approval_request=approval,
        decision=decision_code,
        rationale=rationale,
        decided_by=decided_by,
        metadata=metadata or {},
    )
    return approval


def _apply_runbook_checkpoint_decision(*, approval: ApprovalRequest, decision: str, reviewer: str) -> None:
    checkpoint = RunbookApprovalCheckpoint.objects.select_related('autopilot_run').get(pk=int(approval.source_object_id))
    if decision == ApprovalDecisionType.ESCALATE:
        checkpoint.status = RunbookApprovalCheckpointStatus.REJECTED
        checkpoint.resolved_by = reviewer
        checkpoint.approved_at = timezone.now()
        checkpoint.save(update_fields=['status', 'resolved_by', 'approved_at', 'updated_at'])
        return
    if decision == ApprovalDecisionType.EXPIRE:
        checkpoint.status = RunbookApprovalCheckpointStatus.EXPIRED
        checkpoint.resolved_by = reviewer
        checkpoint.approved_at = timezone.now()
        checkpoint.save(update_fields=['status', 'resolved_by', 'approved_at', 'updated_at'])
        return

    continue_autopilot(
        autopilot_run=checkpoint.autopilot_run,
        checkpoint=checkpoint,
        approved=decision == ApprovalDecisionType.APPROVE,
        reviewer=reviewer,
    )


def _apply_go_live_decision(*, approval: ApprovalRequest, decision: str) -> None:
    request = GoLiveApprovalRequest.objects.get(pk=int(approval.source_object_id))
    if decision == ApprovalDecisionType.APPROVE:
        request.status = GoLiveApprovalStatus.APPROVED
    elif decision in {ApprovalDecisionType.REJECT, ApprovalDecisionType.ESCALATE}:
        request.status = GoLiveApprovalStatus.REJECTED
    elif decision == ApprovalDecisionType.EXPIRE:
        request.status = GoLiveApprovalStatus.EXPIRED
    request.save(update_fields=['status', 'updated_at'])


def _apply_operator_queue_decision(*, approval: ApprovalRequest, decision: str, rationale: str, decided_by: str) -> None:
    item = OperatorQueueItem.objects.get(pk=int(approval.source_object_id))
    if decision == ApprovalDecisionType.APPROVE:
        approve_queue_item(item=item, decision_note=rationale, decided_by=decided_by)
    elif decision == ApprovalDecisionType.REJECT:
        reject_queue_item(item=item, decision_note=rationale, decided_by=decided_by)
    elif decision == ApprovalDecisionType.EXPIRE:
        item.status = OperatorQueueStatus.EXPIRED
        item.save(update_fields=['status', 'updated_at'])
    elif decision == ApprovalDecisionType.ESCALATE:
        item.metadata = {**(item.metadata or {}), 'escalated_by_approval_center': True}
        item.save(update_fields=['metadata', 'updated_at'])
        item.decision_logs.create(decision=OperatorDecisionType.FORCE_BLOCK, decided_by=decided_by, decision_note=rationale)

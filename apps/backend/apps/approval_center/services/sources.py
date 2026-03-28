from __future__ import annotations

from dataclasses import dataclass

from apps.approval_center.models import ApprovalPriority, ApprovalRequestStatus, ApprovalSourceType
from apps.go_live_gate.models import GoLiveApprovalRequest, GoLiveApprovalStatus
from apps.operator_queue.models import OperatorQueueItem, OperatorQueuePriority, OperatorQueueStatus, OperatorQueueType
from apps.runbook_engine.models import RunbookApprovalCheckpoint, RunbookApprovalCheckpointStatus


@dataclass(slots=True)
class ApprovalSourceRecord:
    source_type: str
    source_object_id: str
    title: str
    summary: str
    priority: str
    status: str
    requested_at: object
    expires_at: object
    metadata: dict


RUNBOOK_STATUS_MAP = {
    RunbookApprovalCheckpointStatus.PENDING: ApprovalRequestStatus.PENDING,
    RunbookApprovalCheckpointStatus.APPROVED: ApprovalRequestStatus.APPROVED,
    RunbookApprovalCheckpointStatus.REJECTED: ApprovalRequestStatus.REJECTED,
    RunbookApprovalCheckpointStatus.EXPIRED: ApprovalRequestStatus.EXPIRED,
}
GO_LIVE_STATUS_MAP = {
    GoLiveApprovalStatus.DRAFT: ApprovalRequestStatus.CANCELLED,
    GoLiveApprovalStatus.PENDING: ApprovalRequestStatus.PENDING,
    GoLiveApprovalStatus.APPROVED: ApprovalRequestStatus.APPROVED,
    GoLiveApprovalStatus.REJECTED: ApprovalRequestStatus.REJECTED,
    GoLiveApprovalStatus.EXPIRED: ApprovalRequestStatus.EXPIRED,
}
OPERATOR_STATUS_MAP = {
    OperatorQueueStatus.PENDING: ApprovalRequestStatus.PENDING,
    OperatorQueueStatus.SNOOZED: ApprovalRequestStatus.PENDING,
    OperatorQueueStatus.APPROVED: ApprovalRequestStatus.APPROVED,
    OperatorQueueStatus.EXECUTED: ApprovalRequestStatus.APPROVED,
    OperatorQueueStatus.REJECTED: ApprovalRequestStatus.REJECTED,
    OperatorQueueStatus.EXPIRED: ApprovalRequestStatus.EXPIRED,
}


OPERATOR_PRIORITY_MAP = {
    OperatorQueuePriority.LOW: ApprovalPriority.LOW,
    OperatorQueuePriority.MEDIUM: ApprovalPriority.MEDIUM,
    OperatorQueuePriority.HIGH: ApprovalPriority.HIGH,
    OperatorQueuePriority.CRITICAL: ApprovalPriority.CRITICAL,
}


RUNBOOK_PRIORITY_FROM_INSTANCE = {
    'LOW': ApprovalPriority.LOW,
    'MEDIUM': ApprovalPriority.MEDIUM,
    'HIGH': ApprovalPriority.HIGH,
    'CRITICAL': ApprovalPriority.CRITICAL,
}


def collect_approval_source_records() -> list[ApprovalSourceRecord]:
    records: list[ApprovalSourceRecord] = []

    checkpoints = RunbookApprovalCheckpoint.objects.select_related('runbook_instance', 'runbook_step', 'autopilot_run').order_by('-created_at')[:200]
    for checkpoint in checkpoints:
        records.append(
            ApprovalSourceRecord(
                source_type=ApprovalSourceType.RUNBOOK_CHECKPOINT,
                source_object_id=str(checkpoint.id),
                title=f'Runbook approval checkpoint #{checkpoint.id}',
                summary=checkpoint.approval_reason,
                priority=RUNBOOK_PRIORITY_FROM_INSTANCE.get(checkpoint.runbook_instance.priority, ApprovalPriority.MEDIUM),
                status=RUNBOOK_STATUS_MAP.get(checkpoint.status, ApprovalRequestStatus.PENDING),
                requested_at=checkpoint.created_at,
                expires_at=None,
                metadata={
                    'runbook_instance_id': checkpoint.runbook_instance_id,
                    'runbook_step_id': checkpoint.runbook_step_id,
                    'runbook_step_title': checkpoint.runbook_step.title,
                    'autopilot_run_id': checkpoint.autopilot_run_id,
                    'blocking_constraints': checkpoint.blocking_constraints,
                    'context_snapshot': checkpoint.context_snapshot,
                    'trace': {'root_type': 'runbook_checkpoint', 'root_id': str(checkpoint.id)},
                },
            )
        )

    go_live_requests = GoLiveApprovalRequest.objects.select_related('checklist_run').order_by('-created_at')[:200]
    for request in go_live_requests:
        records.append(
            ApprovalSourceRecord(
                source_type=ApprovalSourceType.GO_LIVE_REQUEST,
                source_object_id=str(request.id),
                title=f'Go-live approval request #{request.id}',
                summary=request.rationale or 'Manual approval required before advancing rehearsal workflow.',
                priority=ApprovalPriority.HIGH,
                status=GO_LIVE_STATUS_MAP.get(request.status, ApprovalRequestStatus.PENDING),
                requested_at=request.created_at,
                expires_at=None,
                metadata={
                    'requested_by': request.requested_by,
                    'scope': request.scope,
                    'requested_mode': request.requested_mode,
                    'blocking_reasons': request.blocking_reasons,
                    'checklist_run_id': request.checklist_run_id,
                    'paper_only': True,
                    'trace': {'root_type': 'go_live_approval', 'root_id': str(request.id)},
                },
            )
        )

    queue_items = OperatorQueueItem.objects.filter(queue_type=OperatorQueueType.APPROVAL_REQUIRED).order_by('-created_at')[:200]
    for item in queue_items:
        records.append(
            ApprovalSourceRecord(
                source_type=ApprovalSourceType.OPERATOR_QUEUE_ITEM,
                source_object_id=str(item.id),
                title=item.headline,
                summary=item.summary,
                priority=OPERATOR_PRIORITY_MAP.get(item.priority, ApprovalPriority.MEDIUM),
                status=OPERATOR_STATUS_MAP.get(item.status, ApprovalRequestStatus.PENDING),
                requested_at=item.created_at,
                expires_at=item.expires_at,
                metadata={
                    'operator_queue_source': item.source,
                    'operator_queue_type': item.queue_type,
                    'rationale': item.rationale,
                    'suggested_action': item.suggested_action,
                    'suggested_quantity': str(item.suggested_quantity) if item.suggested_quantity is not None else None,
                    'related_proposal_id': item.related_proposal_id,
                    'related_market_id': item.related_market_id,
                    'related_pending_approval_id': item.related_pending_approval_id,
                    'trace': {'root_type': 'operator_queue_item', 'root_id': str(item.id)},
                },
            )
        )

    return records

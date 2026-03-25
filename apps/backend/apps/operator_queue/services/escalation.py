from __future__ import annotations

from apps.operator_queue.models import (
    OperatorQueueItem,
    OperatorQueuePriority,
    OperatorQueueSource,
    OperatorQueueStatus,
    OperatorQueueType,
)
from apps.semi_auto_demo.models import PendingApproval, PendingApprovalStatus


def _source_from_pending(pending: PendingApproval) -> str:
    source = (pending.metadata or {}).get('source', 'semi_auto_demo')
    if source == 'real_market_ops':
        return OperatorQueueSource.REAL_OPS
    if source == 'safety_guard':
        return OperatorQueueSource.SAFETY
    return OperatorQueueSource.SEMI_AUTO


def _priority_from_pending(pending: PendingApproval) -> str:
    source = _source_from_pending(pending)
    if source == OperatorQueueSource.REAL_OPS and pending.market and pending.market.source_type == 'REAL_READ_ONLY':
        return OperatorQueuePriority.HIGH
    if source == OperatorQueueSource.SAFETY:
        return OperatorQueuePriority.HIGH
    return OperatorQueuePriority.MEDIUM


def ensure_queue_item_for_pending_approval(*, pending_approval: PendingApproval) -> OperatorQueueItem:
    existing = OperatorQueueItem.objects.filter(
        related_pending_approval=pending_approval,
        status__in=[OperatorQueueStatus.PENDING, OperatorQueueStatus.SNOOZED],
    ).order_by('-created_at').first()
    if existing:
        return existing

    return OperatorQueueItem.objects.create(
        status=OperatorQueueStatus.PENDING,
        source=_source_from_pending(pending_approval),
        queue_type=OperatorQueueType.APPROVAL_REQUIRED,
        related_proposal=pending_approval.proposal,
        related_market=pending_approval.market,
        related_pending_approval=pending_approval,
        priority=_priority_from_pending(pending_approval),
        headline=pending_approval.summary,
        summary=pending_approval.summary,
        rationale=pending_approval.rationale,
        suggested_action=pending_approval.requested_action,
        suggested_quantity=pending_approval.suggested_quantity,
        expires_at=pending_approval.proposal.expires_at,
        metadata={
            **(pending_approval.metadata or {}),
            'pending_approval_id': pending_approval.id,
            'execution_mode': 'paper_demo_only',
            'operator_review_reason': 'Pending approval requires manual operator decision.',
        },
    )


def rebuild_from_pending_approvals() -> int:
    before = OperatorQueueItem.objects.count()
    for pending in PendingApproval.objects.filter(status=PendingApprovalStatus.PENDING).select_related('proposal', 'market'):
        ensure_queue_item_for_pending_approval(pending_approval=pending)
    after = OperatorQueueItem.objects.count()
    return max(after - before, 0)

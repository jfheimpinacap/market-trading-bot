from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from apps.operator_queue.models import (
    OperatorDecisionLog,
    OperatorDecisionType,
    OperatorQueueItem,
    OperatorQueueStatus,
)
from apps.paper_trading.services.execution import execute_paper_trade
from apps.paper_trading.services.portfolio import get_active_account


def _log_decision(*, item: OperatorQueueItem, decision: str, note: str, decided_by: str, metadata: dict | None = None) -> OperatorDecisionLog:
    return OperatorDecisionLog.objects.create(
        queue_item=item,
        decision=decision,
        decided_by=decided_by,
        decision_note=note,
        metadata=metadata or {},
    )


def approve_queue_item(*, item: OperatorQueueItem, decision_note: str = '', decided_by: str = 'local-operator') -> OperatorQueueItem:
    if item.status not in {OperatorQueueStatus.PENDING, OperatorQueueStatus.SNOOZED}:
        raise ValueError('Only PENDING/SNOOZED queue items can be approved.')

    trade = None
    execution_metadata: dict = {'path': 'operator_queue'}

    if item.related_pending_approval_id:
        from apps.semi_auto_demo.services.execution import approve_pending_approval
        pending = approve_pending_approval(pending_approval=item.related_pending_approval, decision_note=decision_note)
        trade = pending.executed_trade
        item.status = OperatorQueueStatus.EXECUTED if trade else OperatorQueueStatus.APPROVED
    elif item.related_proposal_id and item.suggested_action in {'BUY', 'SELL'} and item.related_proposal.suggested_side and item.suggested_quantity:
        account = item.related_proposal.paper_account or get_active_account()
        execution = execute_paper_trade(
            market=item.related_proposal.market,
            trade_type=item.suggested_action,
            side=item.related_proposal.suggested_side,
            quantity=item.suggested_quantity,
            account=account,
            notes='Operator queue approved execution (paper/demo).',
            metadata={'operator_queue_item_id': item.id, 'execution_origin': 'operator_approval_queue'},
        )
        trade = execution.trade
        item.status = OperatorQueueStatus.EXECUTED
        execution_metadata['path'] = 'proposal_direct_execution'
    else:
        item.status = OperatorQueueStatus.APPROVED

    item.snoozed_until = None
    if trade:
        item.related_trade = trade
    item.save(update_fields=['status', 'snoozed_until', 'related_trade', 'updated_at'])
    _log_decision(item=item, decision=OperatorDecisionType.APPROVE, note=decision_note, decided_by=decided_by, metadata=execution_metadata)
    return item


def reject_queue_item(*, item: OperatorQueueItem, decision_note: str = '', decided_by: str = 'local-operator') -> OperatorQueueItem:
    if item.status not in {OperatorQueueStatus.PENDING, OperatorQueueStatus.SNOOZED}:
        raise ValueError('Only PENDING/SNOOZED queue items can be rejected.')

    if item.related_pending_approval_id and item.related_pending_approval.status == 'PENDING':
        from apps.semi_auto_demo.services.execution import reject_pending_approval
        reject_pending_approval(pending_approval=item.related_pending_approval, decision_note=decision_note)

    item.status = OperatorQueueStatus.REJECTED
    item.snoozed_until = None
    item.save(update_fields=['status', 'snoozed_until', 'updated_at'])
    _log_decision(item=item, decision=OperatorDecisionType.REJECT, note=decision_note, decided_by=decided_by)
    return item


def snooze_queue_item(*, item: OperatorQueueItem, decision_note: str = '', snooze_until=None, snooze_hours: int = 6, decided_by: str = 'local-operator') -> OperatorQueueItem:
    if item.status not in {OperatorQueueStatus.PENDING, OperatorQueueStatus.SNOOZED}:
        raise ValueError('Only PENDING/SNOOZED queue items can be snoozed.')

    target = snooze_until or (timezone.now() + timedelta(hours=snooze_hours))
    item.status = OperatorQueueStatus.SNOOZED
    item.snoozed_until = target
    item.save(update_fields=['status', 'snoozed_until', 'updated_at'])
    _log_decision(
        item=item,
        decision=OperatorDecisionType.SNOOZE,
        note=decision_note,
        decided_by=decided_by,
        metadata={'snoozed_until': target.isoformat()},
    )
    return item

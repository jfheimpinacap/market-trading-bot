from __future__ import annotations

from django.utils import timezone

from apps.paper_trading.services.execution import execute_paper_trade
from apps.semi_auto_demo.models import PendingApproval, PendingApprovalStatus


def approve_pending_approval(*, pending_approval: PendingApproval, decision_note: str = '') -> PendingApproval:
    if pending_approval.status != PendingApprovalStatus.PENDING:
        raise ValueError('Only PENDING approvals can be approved.')

    result = execute_paper_trade(
        market=pending_approval.market,
        trade_type=pending_approval.requested_action,
        side=pending_approval.suggested_side,
        quantity=pending_approval.suggested_quantity,
        account=pending_approval.paper_account,
        notes='Semi-auto pending approval executed manually.',
        metadata={
            'semi_auto_pending_approval_id': pending_approval.id,
            'semi_auto_proposal_id': pending_approval.proposal_id,
            'semi_auto_execution_origin': 'manual_approval',
        },
    )

    pending_approval.status = PendingApprovalStatus.EXECUTED
    pending_approval.executed_trade = result.trade
    pending_approval.decided_at = timezone.now()
    pending_approval.decision_note = decision_note
    pending_approval.save(update_fields=['status', 'executed_trade', 'decided_at', 'decision_note', 'updated_at'])
    return pending_approval


def reject_pending_approval(*, pending_approval: PendingApproval, decision_note: str = '') -> PendingApproval:
    if pending_approval.status != PendingApprovalStatus.PENDING:
        raise ValueError('Only PENDING approvals can be rejected.')

    pending_approval.status = PendingApprovalStatus.REJECTED
    pending_approval.decided_at = timezone.now()
    pending_approval.decision_note = decision_note
    pending_approval.save(update_fields=['status', 'decided_at', 'decision_note', 'updated_at'])
    return pending_approval

from __future__ import annotations

from apps.autonomous_trader.models import AutonomousOutcomeStatus, AutonomousOutcomeType, AutonomousTradeExecution, AutonomousTradeOutcome, AutonomousTradeWatchRecord


def create_outcome(*, execution: AutonomousTradeExecution, watch_record: AutonomousTradeWatchRecord | None = None) -> AutonomousTradeOutcome:
    trade = execution.linked_paper_trade
    if execution.execution_status in {'SKIPPED', 'NO_FILL', 'CANCELLED'}:
        outcome_type = AutonomousOutcomeType.BLOCKED_PRE_TRADE
        outcome_status = AutonomousOutcomeStatus.CLOSED
        send_to_postmortem = False
    elif trade and trade.position and trade.position.status == 'CLOSED':
        pnl = trade.position.realized_pnl + trade.position.unrealized_pnl
        if pnl < 0:
            outcome_type = AutonomousOutcomeType.LOSS_EXIT
            send_to_postmortem = True
        else:
            outcome_type = AutonomousOutcomeType.PROFITABLE_EXIT
            send_to_postmortem = False
        outcome_status = AutonomousOutcomeStatus.CLOSED
    else:
        outcome_type = AutonomousOutcomeType.NO_ACTION
        outcome_status = AutonomousOutcomeStatus.OPEN
        send_to_postmortem = False

    send_to_learning = outcome_status == AutonomousOutcomeStatus.CLOSED
    return AutonomousTradeOutcome.objects.create(
        linked_execution=execution,
        linked_watch_record=watch_record,
        outcome_type=outcome_type,
        outcome_status=outcome_status,
        outcome_summary='Outcome recorded by autonomous paper cycle.',
        send_to_postmortem=send_to_postmortem,
        send_to_learning=send_to_learning,
        metadata={'paper_only': True},
    )

from __future__ import annotations

from decimal import Decimal

from django.db import transaction

from apps.autonomous_trader.models import (
    AutonomousPositionActionDecisionStatus,
    AutonomousPositionActionDecisionType,
    AutonomousPositionActionExecution,
    AutonomousPositionActionExecutionStatus,
    AutonomousPositionActionExecutionType,
)
from apps.paper_trading.models import PaperTradeType
from apps.paper_trading.services.execution import PaperTradingRejectionError, execute_paper_trade


@transaction.atomic
def execute_action(*, decision) -> AutonomousPositionActionExecution | None:
    candidate = decision.linked_watch_candidate
    position = candidate.linked_position
    if not position or not position.quantity or position.quantity <= 0:
        decision.decision_status = AutonomousPositionActionDecisionStatus.SKIPPED
        decision.save(update_fields=['decision_status', 'updated_at'])
        return None

    quantity_before = position.quantity
    notional_before = position.market_value

    if decision.decision_type == AutonomousPositionActionDecisionType.HOLD_POSITION:
        decision.decision_status = AutonomousPositionActionDecisionStatus.SKIPPED
        decision.save(update_fields=['decision_status', 'updated_at'])
        return None

    if decision.decision_type == AutonomousPositionActionDecisionType.REVIEW_REQUIRED:
        decision.decision_status = AutonomousPositionActionDecisionStatus.BLOCKED
        decision.save(update_fields=['decision_status', 'updated_at'])
        return AutonomousPositionActionExecution.objects.create(
            linked_action_decision=decision,
            linked_position=position,
            execution_type=AutonomousPositionActionExecutionType.REDUCE_EXECUTION,
            execution_status=AutonomousPositionActionExecutionStatus.BLOCKED,
            quantity_before=quantity_before,
            quantity_after=quantity_before,
            notional_before=notional_before,
            notional_after=notional_before,
            summary='Review required blocked autonomous execution.',
            metadata={'paper_only': True},
        )

    close = decision.decision_type == AutonomousPositionActionDecisionType.CLOSE_POSITION
    execution_type = AutonomousPositionActionExecutionType.CLOSE_EXECUTION if close else AutonomousPositionActionExecutionType.REDUCE_EXECUTION
    fraction = Decimal('1.0') if close else Decimal(str(decision.reduction_fraction or '0.2500'))
    sell_qty = (quantity_before * fraction).quantize(Decimal('0.0001'))
    if sell_qty <= Decimal('0.0000'):
        sell_qty = quantity_before

    try:
        result = execute_paper_trade(
            market=position.market,
            trade_type=PaperTradeType.SELL,
            side=position.side,
            quantity=sell_qty,
            account=position.account,
            notes='Autonomous position-watch action execution (paper-only).',
            metadata={'source': 'autonomous_position_watch', 'decision_id': decision.id, 'paper_only': True},
        )
        position.refresh_from_db()
        decision.decision_status = AutonomousPositionActionDecisionStatus.APPLIED
        decision.save(update_fields=['decision_status', 'updated_at'])
        return AutonomousPositionActionExecution.objects.create(
            linked_action_decision=decision,
            linked_position=position,
            linked_paper_trade=result.trade,
            execution_type=execution_type,
            execution_status=AutonomousPositionActionExecutionStatus.FILLED,
            quantity_before=quantity_before,
            quantity_after=position.quantity,
            notional_before=notional_before,
            notional_after=position.market_value,
            summary='Paper execution filled for autonomous post-entry management.',
            metadata={'paper_only': True, 'executed_quantity': str(sell_qty)},
        )
    except PaperTradingRejectionError as exc:
        decision.decision_status = AutonomousPositionActionDecisionStatus.BLOCKED
        decision.save(update_fields=['decision_status', 'updated_at'])
        return AutonomousPositionActionExecution.objects.create(
            linked_action_decision=decision,
            linked_position=position,
            execution_type=execution_type,
            execution_status=AutonomousPositionActionExecutionStatus.NO_FILL,
            quantity_before=quantity_before,
            quantity_after=quantity_before,
            notional_before=notional_before,
            notional_after=notional_before,
            summary=str(exc),
            metadata={'paper_only': True, 'error': str(exc)},
        )

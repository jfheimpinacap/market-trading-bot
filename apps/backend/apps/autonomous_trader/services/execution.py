from __future__ import annotations

from decimal import Decimal

from apps.autonomous_trader.models import AutonomousExecutionStatus, AutonomousTradeDecision, AutonomousTradeExecution
from apps.paper_trading.models import PaperTradeType
from apps.paper_trading.services.execution import PaperTradingValidationError, execute_paper_trade


def execute_candidate(*, decision: AutonomousTradeDecision) -> AutonomousTradeExecution:
    candidate = decision.linked_candidate
    if decision.decision_type != 'EXECUTE_PAPER_TRADE':
        return AutonomousTradeExecution.objects.create(
            linked_candidate=candidate,
            linked_decision=decision,
            execution_status=AutonomousExecutionStatus.SKIPPED,
            sizing_summary='No execution due to decision type.',
            watch_plan_summary='Watch path only.',
            metadata={'paper_only': True},
        )

    sizing_decision = candidate.sizing_decisions.order_by('-created_at', '-id').first()
    notional = sizing_decision.notional_after_adjustment if sizing_decision and sizing_decision.notional_after_adjustment else Decimal('50.00')
    market_probability = candidate.market_probability or Decimal('0.50')
    price = max(Decimal('0.10'), min(Decimal('0.90'), market_probability))
    quantity = sizing_decision.final_paper_quantity if sizing_decision and sizing_decision.final_paper_quantity else (notional / price).quantize(Decimal('0.0001'))

    try:
        result = execute_paper_trade(
            market=candidate.linked_market,
            trade_type=PaperTradeType.BUY,
            side='YES',
            quantity=quantity,
            notes='autonomous trader paper cycle',
            metadata={'source': 'autonomous_trader', 'candidate_id': candidate.id},
            execution_price=price,
        )
    except PaperTradingValidationError as exc:
        return AutonomousTradeExecution.objects.create(
            linked_candidate=candidate,
            linked_decision=decision,
            linked_sizing_decision=sizing_decision,
            execution_status=AutonomousExecutionStatus.NO_FILL,
            sizing_summary=f'Execution blocked: {exc}',
            watch_plan_summary='No watch plan due to failed submission.',
            metadata={'paper_only': True, 'error': str(exc)},
        )

    decision.decision_status = 'EXECUTED'
    decision.save(update_fields=['decision_status', 'updated_at'])

    return AutonomousTradeExecution.objects.create(
        linked_candidate=candidate,
        linked_decision=decision,
        linked_sizing_decision=sizing_decision,
        linked_paper_trade=result.trade,
        execution_status=AutonomousExecutionStatus.FILLED,
        sizing_summary=f'notional={notional} quantity={quantity} price={price} sizing_decision_id={sizing_decision.id if sizing_decision else None}',
        watch_plan_summary='Track drift, risk change and position PnL each cycle.',
        metadata={'paper_only': True, 'paper_trade_id': result.trade.id, 'sizing_decision_id': sizing_decision.id if sizing_decision else None},
    )

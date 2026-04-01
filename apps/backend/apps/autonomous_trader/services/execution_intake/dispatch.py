from __future__ import annotations

from decimal import Decimal

from apps.autonomous_trader.models import (
    AutonomousDispatchMode,
    AutonomousDispatchRecord,
    AutonomousDispatchStatus,
    AutonomousExecutionDecision,
    AutonomousExecutionDecisionStatus,
    AutonomousExecutionDecisionType,
    AutonomousExecutionStatus,
    AutonomousTradeDecision,
    AutonomousTradeCandidate,
    AutonomousTradeExecution,
)
from apps.paper_trading.models import PaperTradeType
from apps.paper_trading.services.execution import PaperTradingValidationError, execute_paper_trade


SKIP_TYPES = {
    AutonomousExecutionDecisionType.KEEP_ON_WATCH,
    AutonomousExecutionDecisionType.DEFER,
    AutonomousExecutionDecisionType.BLOCK,
    AutonomousExecutionDecisionType.REQUIRE_MANUAL_REVIEW,
}


def dispatch_execution_decision(*, decision: AutonomousExecutionDecision) -> AutonomousDispatchRecord:
    intake_candidate = decision.linked_intake_candidate

    if decision.decision_type in SKIP_TYPES:
        status = AutonomousDispatchStatus.BLOCKED if decision.decision_type in {AutonomousExecutionDecisionType.BLOCK, AutonomousExecutionDecisionType.REQUIRE_MANUAL_REVIEW} else AutonomousDispatchStatus.SKIPPED
        return AutonomousDispatchRecord.objects.create(
            linked_execution_decision=decision,
            dispatch_status=status,
            dispatch_mode=AutonomousDispatchMode.PAPER_EXECUTION,
            dispatch_summary='Dispatch skipped by explicit non-execution decision.',
            metadata={'paper_only': True},
        )

    sizing_plan = intake_candidate.linked_sizing_plan
    notional = Decimal(sizing_plan.paper_notional_size) if sizing_plan and sizing_plan.paper_notional_size else Decimal('50.00')
    if decision.decision_type == AutonomousExecutionDecisionType.EXECUTE_REDUCED:
        notional = (notional * Decimal('0.50')).quantize(Decimal('0.01'))

    market_probability = Decimal('0.50')
    linked_readiness = intake_candidate.linked_execution_readiness
    if linked_readiness and linked_readiness.linked_approval_review and linked_readiness.linked_approval_review.linked_candidate.market_probability:
        market_probability = linked_readiness.linked_approval_review.linked_candidate.market_probability
    price = max(Decimal('0.10'), min(Decimal('0.90'), market_probability))
    quantity = (notional / price).quantize(Decimal('0.0001')) if price > 0 else Decimal('0.0000')

    if quantity <= 0:
        decision.decision_status = AutonomousExecutionDecisionStatus.BLOCKED
        decision.save(update_fields=['decision_status', 'updated_at'])
        return AutonomousDispatchRecord.objects.create(
            linked_execution_decision=decision,
            dispatch_status=AutonomousDispatchStatus.BLOCKED,
            dispatch_mode=AutonomousDispatchMode.PAPER_EXECUTION,
            dispatch_summary='Dispatch blocked: non-positive quantity.',
            metadata={'paper_only': True, 'reason': 'NON_POSITIVE_QUANTITY'},
        )

    try:
        result = execute_paper_trade(
            market=intake_candidate.linked_market,
            trade_type=PaperTradeType.BUY,
            side='YES',
            quantity=quantity,
            notes='autonomous execution intake dispatch',
            metadata={'source': 'autonomous_execution_intake', 'intake_candidate_id': intake_candidate.id},
            execution_price=price,
        )
    except PaperTradingValidationError as exc:
        decision.decision_status = AutonomousExecutionDecisionStatus.BLOCKED
        decision.save(update_fields=['decision_status', 'updated_at'])
        return AutonomousDispatchRecord.objects.create(
            linked_execution_decision=decision,
            dispatch_status=AutonomousDispatchStatus.BLOCKED,
            dispatch_mode=AutonomousDispatchMode.PAPER_EXECUTION,
            dispatched_notional=notional,
            dispatched_quantity=quantity,
            dispatch_summary=f'Paper dispatch blocked: {exc}',
            metadata={'paper_only': True, 'error': str(exc)},
        )

    trade_candidate = AutonomousTradeCandidate.objects.create(
        cycle_run=intake_candidate.intake_run.linked_cycle_run,
        linked_market=intake_candidate.linked_market,
        linked_risk_recommendation=None,
        candidate_status='EXECUTION_READY',
        adjusted_edge=Decimal('0.0000'),
        confidence=decision.decision_confidence,
        risk_posture=intake_candidate.approval_status or 'UNKNOWN',
        metadata={'source': 'autonomous_execution_intake', 'intake_candidate_id': intake_candidate.id},
    )

    trade_execution = AutonomousTradeExecution.objects.create(
        linked_candidate=trade_candidate,
        linked_decision=AutonomousTradeDecision.objects.create(
            linked_candidate=trade_candidate,
            decision_type='EXECUTE_PAPER_TRADE',
            decision_status='EXECUTED',
            rationale='Legacy execution record emitted from readiness-driven dispatch bridge.',
            reason_codes=['READINESS_DISPATCH_BRIDGE'],
            metadata={'execution_decision_id': decision.id},
        ),
        linked_paper_trade=result.trade,
        execution_status=AutonomousExecutionStatus.FILLED,
        sizing_summary=f'notional={notional} quantity={quantity} price={price}',
        watch_plan_summary=intake_candidate.linked_watch_plan.review_interval_hint if intake_candidate.linked_watch_plan else 'No watch plan attached.',
        metadata={'paper_only': True, 'dispatch_bridge': 'execution_intake'},
    )

    decision.decision_status = AutonomousExecutionDecisionStatus.APPLIED
    decision.save(update_fields=['decision_status', 'updated_at'])

    return AutonomousDispatchRecord.objects.create(
        linked_execution_decision=decision,
        linked_trade_execution=trade_execution,
        linked_paper_trade=result.trade,
        dispatch_status=AutonomousDispatchStatus.FILLED,
        dispatch_mode=AutonomousDispatchMode.PAPER_REDUCED_EXECUTION if decision.decision_type == AutonomousExecutionDecisionType.EXECUTE_REDUCED else AutonomousDispatchMode.PAPER_EXECUTION,
        dispatched_notional=notional,
        dispatched_quantity=quantity,
        dispatch_summary='Paper dispatch completed from readiness-driven intake decision.',
        metadata={'paper_only': True, 'paper_trade_id': result.trade.id},
    )

from __future__ import annotations

from django.db import transaction

from apps.operator_queue.models import OperatorQueueItem, OperatorQueuePriority, OperatorQueueSource, OperatorQueueStatus, OperatorQueueType
from apps.paper_trading.models import PaperPositionStatus, PaperTradeType
from apps.paper_trading.services.execution import execute_paper_trade
from apps.paper_trading.services.portfolio import get_active_account
from apps.position_manager.models import PositionExitPlan, PositionLifecycleDecision, PositionLifecycleRun, PositionLifecycleRunStatus, PositionLifecycleStatus
from apps.position_manager.services.decision import decide_lifecycle_action
from apps.position_manager.services.exit_plan import build_exit_plan
from apps.position_manager.services.snapshots import build_position_snapshot
from apps.runtime_governor.services import get_capabilities_for_current_mode
from apps.safety_guard.services import get_safety_status


@transaction.atomic
def run_position_lifecycle(*, metadata: dict | None = None) -> PositionLifecycleRun:
    metadata = metadata or {}
    account = get_active_account()
    positions = list(account.positions.filter(status=PaperPositionStatus.OPEN, quantity__gt=0).select_related('market').order_by('-updated_at', '-id'))
    runtime_caps = get_capabilities_for_current_mode()
    safety = get_safety_status()

    run = PositionLifecycleRun.objects.create(status=PositionLifecycleRunStatus.READY, watched_positions=len(positions), metadata=metadata)

    if not positions:
        run.status = PositionLifecycleRunStatus.SUCCESS
        run.summary = 'No open paper positions to review right now.'
        run.save(update_fields=['status', 'summary', 'updated_at'])
        return run

    decisions = []
    for position in positions:
        snapshot, latest_prediction, latest_watch_event = build_position_snapshot(position)
        status, reason_codes, rationale, confidence = decide_lifecycle_action(snapshot)

        decision = PositionLifecycleDecision.objects.create(
            run=run,
            paper_position=position,
            latest_watch_event=latest_watch_event,
            status=status,
            decision_confidence=confidence,
            rationale=rationale,
            reason_codes=reason_codes,
            risk_context={
                'watch_severity': snapshot.get('watch_severity'),
                'latest_watch_event_type': snapshot.get('latest_watch_event_type'),
                'safety_state': snapshot.get('safety_state'),
            },
            prediction_context={
                'prediction_probability': snapshot.get('prediction_probability'),
                'prediction_drift': snapshot.get('prediction_drift'),
                'edge': snapshot.get('current_edge_estimate'),
                'confidence': snapshot.get('confidence'),
                'prediction_score_id': latest_prediction.id if latest_prediction else None,
            },
            narrative_context={
                'narrative_drift': snapshot.get('narrative_drift'),
                'provider_stale': snapshot.get('provider_stale'),
            },
            position_snapshot=snapshot,
            metadata={'paper_demo_only': True},
        )

        plan_data = build_exit_plan(position=position, action=status, reason_codes=reason_codes, runtime_caps=runtime_caps, safety=safety)
        plan = PositionExitPlan.objects.create(decision=decision, paper_position=position, metadata={'paper_demo_only': True}, **plan_data)

        if plan.queue_required:
            OperatorQueueItem.objects.create(
                status=OperatorQueueStatus.PENDING,
                source=OperatorQueueSource.SAFETY,
                queue_type=OperatorQueueType.SAFETY_REVIEW,
                related_market=position.market,
                priority=OperatorQueuePriority.HIGH if status == PositionLifecycleStatus.CLOSE else OperatorQueuePriority.MEDIUM,
                headline=f'Position lifecycle review: {position.market.title}',
                summary=f'{status} suggested for paper position #{position.id}',
                rationale=rationale,
                suggested_action=status,
                suggested_quantity=plan.target_quantity,
                metadata={'position_lifecycle_decision_id': decision.id, 'position_exit_plan_id': plan.id, 'paper_demo_only': True},
            )

        if plan.auto_execute_allowed and plan.quantity_delta > 0:
            execute_paper_trade(
                market=position.market,
                trade_type=PaperTradeType.SELL,
                side=position.side,
                quantity=plan.quantity_delta,
                metadata={'triggered_from': 'position_lifecycle', 'position_exit_plan_id': plan.id, 'paper_demo_only': True},
                notes=f'Lifecycle auto action: {plan.action}',
            )

        decisions.append(decision)

    run.status = PositionLifecycleRunStatus.SUCCESS
    run.decisions_count = len(decisions)
    run.hold_count = sum(1 for item in decisions if item.status == PositionLifecycleStatus.HOLD)
    run.reduce_count = sum(1 for item in decisions if item.status == PositionLifecycleStatus.REDUCE)
    run.close_count = sum(1 for item in decisions if item.status == PositionLifecycleStatus.CLOSE)
    run.review_required_count = sum(1 for item in decisions if item.status == PositionLifecycleStatus.REVIEW_REQUIRED)
    run.summary = (
        f'Lifecycle reviewed {len(decisions)} positions: hold={run.hold_count}, reduce={run.reduce_count}, '
        f'close={run.close_count}, review={run.review_required_count}.'
    )
    run.save(update_fields=['status', 'decisions_count', 'hold_count', 'reduce_count', 'close_count', 'review_required_count', 'summary', 'updated_at'])
    return run

from __future__ import annotations

from decimal import Decimal

from apps.rollout_manager.models import RolloutGuardrailEvent, StackRolloutRun


def _as_decimal(value: object, default: str = '0') -> Decimal:
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal(default)


def evaluate_guardrails(*, run: StackRolloutRun, metrics: dict) -> list[RolloutGuardrailEvent]:
    guardrails = run.plan.guardrails or {}
    events: list[RolloutGuardrailEvent] = []

    checks = [
        ('FILL_RATE_DROP', _as_decimal(metrics.get('fill_rate_delta')), _as_decimal(guardrails.get('min_fill_rate_delta', -0.08)), 'lt', 'Fill rate dropped beyond allowed threshold.'),
        ('NO_FILL_RATE_SPIKE', _as_decimal(metrics.get('no_fill_rate_delta')), _as_decimal(guardrails.get('max_no_fill_rate_delta', 0.12)), 'gt', 'No-fill rate increased too much.'),
        ('EXECUTION_PNL_DEGRADATION', _as_decimal(metrics.get('execution_adjusted_pnl_delta')), _as_decimal(guardrails.get('min_execution_adjusted_pnl_delta', -15)), 'lt', 'Execution-adjusted pnl degraded beyond guardrail.'),
        ('EXECUTION_DRAG_SPIKE', _as_decimal(metrics.get('execution_drag_delta')), _as_decimal(guardrails.get('max_execution_drag_delta', 0.08)), 'gt', 'Execution drag increased too much.'),
        ('QUEUE_PRESSURE_SPIKE', _as_decimal(metrics.get('queue_pressure_delta')), _as_decimal(guardrails.get('max_queue_pressure_delta', 0.20)), 'gt', 'Queue pressure increased too much.'),
        ('DRAWDOWN_STRESS', _as_decimal(metrics.get('drawdown_delta')), _as_decimal(guardrails.get('max_drawdown_delta', 0.03)), 'gt', 'Drawdown/stress degraded beyond threshold.'),
    ]

    for code, value, threshold, op, reason in checks:
        triggered = value < threshold if op == 'lt' else value > threshold
        if triggered:
            events.append(
                RolloutGuardrailEvent.objects.create(
                    run=run,
                    code=code,
                    severity='CRITICAL' if code in {'EXECUTION_PNL_DEGRADATION', 'DRAWDOWN_STRESS'} else 'WARNING',
                    reason=reason,
                    metric_value=value,
                    threshold_value=threshold,
                    metadata={'metrics': metrics},
                )
            )

    if metrics.get('runtime_blocked') or metrics.get('readiness_blocked') or metrics.get('safety_blocked'):
        events.append(
            RolloutGuardrailEvent.objects.create(
                run=run,
                code='RUNTIME_OR_SAFETY_BLOCK',
                severity='CRITICAL',
                reason='Runtime/readiness/safety gate blocked rollout continuation.',
                metadata={'metrics': metrics},
            )
        )

    return events

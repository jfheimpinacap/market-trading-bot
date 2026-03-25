from decimal import Decimal

from apps.experiment_lab.models import ExperimentRun

METRICS = [
    'proposals_generated',
    'trades_executed',
    'approvals_required',
    'blocked_count',
    'favorable_review_rate',
    'total_pnl',
    'ending_equity',
    'equity_delta',
    'safety_events_count',
    'cooldown_count',
    'hard_stop_count',
    'allocation_efficiency',
    'block_rate',
    'auto_execution_rate',
]


def _to_decimal(value: object) -> Decimal:
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal('0')


def compare_experiment_runs(left: ExperimentRun, right: ExperimentRun) -> dict:
    left_metrics = left.normalized_metrics or {}
    right_metrics = right.normalized_metrics or {}

    deltas = {}
    for key in METRICS:
        deltas[key] = str(_to_decimal(right_metrics.get(key)) - _to_decimal(left_metrics.get(key)))

    interpretation = []
    if _to_decimal(deltas['block_rate']) < 0 and _to_decimal(deltas['auto_execution_rate']) < 0:
        interpretation.append('Right run appears more conservative (lower auto-execution and lower block pressure).')
    if _to_decimal(deltas['total_pnl']) > 0:
        interpretation.append('Right run produced higher total PnL.')
    if _to_decimal(deltas['safety_events_count']) > 0:
        interpretation.append('Right run triggered more safety events; review guardrail thresholds.')
    if not interpretation:
        interpretation.append('Runs are close; use more samples across replay and live paper evaluation.')

    return {
        'left_run': {'id': left.id, 'profile': left.strategy_profile.slug, 'run_type': left.run_type, 'metrics': left_metrics},
        'right_run': {'id': right.id, 'profile': right.strategy_profile.slug, 'run_type': right.run_type, 'metrics': right_metrics},
        'delta': deltas,
        'interpretation': interpretation,
    }

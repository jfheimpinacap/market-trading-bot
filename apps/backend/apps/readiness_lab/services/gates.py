from dataclasses import dataclass


@dataclass
class GateResult:
    gate: str
    expected: float | int
    actual: float | int
    comparator: str
    passed: bool
    severity: str
    reason: str


def _evaluate_min(gate: str, expected: float | int, actual: float | int, severity: str, reason: str) -> GateResult:
    return GateResult(
        gate=gate,
        expected=expected,
        actual=actual,
        comparator='>=',
        passed=actual >= expected,
        severity=severity,
        reason=reason,
    )


def _evaluate_max(gate: str, expected: float | int, actual: float | int, severity: str, reason: str) -> GateResult:
    return GateResult(
        gate=gate,
        expected=expected,
        actual=actual,
        comparator='<=',
        passed=actual <= expected,
        severity=severity,
        reason=reason,
    )


def evaluate_gates(config: dict, metrics: dict) -> list[GateResult]:
    return [
        _evaluate_min('minimum_replay_runs', config.get('minimum_replay_runs', 0), metrics['replay_runs_count'], 'critical', 'Replay evidence is below required minimum.'),
        _evaluate_min('minimum_live_paper_runs', config.get('minimum_live_paper_runs', 0), metrics['evaluation_runs_count'], 'critical', 'Live-paper evaluation evidence is below required minimum.'),
        _evaluate_min('minimum_favorable_review_rate', config.get('minimum_favorable_review_rate', 0), metrics['favorable_review_rate'], 'critical', 'Favorable review rate is below threshold.'),
        _evaluate_max('maximum_block_rate', config.get('maximum_block_rate', 1), metrics['block_rate'], 'warning', 'Block rate is above profile tolerance.'),
        _evaluate_max('maximum_safety_event_rate', config.get('maximum_safety_event_rate', 1), metrics['safety_event_rate'], 'critical', 'Safety event rate exceeds profile tolerance.'),
        _evaluate_max('maximum_hard_stop_count', config.get('maximum_hard_stop_count', 0), metrics['hard_stop_count'], 'critical', 'Hard stop events must be reduced.'),
        _evaluate_max('maximum_drawdown', config.get('maximum_drawdown', 0), metrics['max_drawdown_value'], 'critical', 'Drawdown is above configured threshold.'),
        _evaluate_min('minimum_stability_window', config.get('minimum_stability_window', 0), metrics['stability_window_count'], 'warning', 'Too few stable evaluation runs.'),
        _evaluate_max('maximum_operator_intervention_rate', config.get('maximum_operator_intervention_rate', 1), metrics['operator_intervention_rate'], 'warning', 'Operator intervention dependency remains high.'),
        _evaluate_min('minimum_real_market_ops_coverage', config.get('minimum_real_market_ops_coverage', 0), metrics['real_market_ops_coverage'], 'warning', 'Insufficient real read-only coverage for promotion confidence.'),
        _evaluate_min('minimum_experiment_comparison_consistency', config.get('minimum_experiment_comparison_consistency', 0), metrics['experiment_consistency_rate'], 'warning', 'Replay-vs-live experiment consistency is below target.'),
    ]

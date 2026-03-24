from apps.evaluation_lab.models import EvaluationRun


def compare_runs(left: EvaluationRun, right: EvaluationRun) -> dict:
    left_metrics = getattr(left, 'metric_set', None)
    right_metrics = getattr(right, 'metric_set', None)
    if not left_metrics or not right_metrics:
        return {'detail': 'Both runs must include a metric set.'}

    return {
        'left_run_id': left.id,
        'right_run_id': right.id,
        'delta': {
            'total_pnl': right_metrics.total_pnl - left_metrics.total_pnl,
            'equity_delta': right_metrics.equity_delta - left_metrics.equity_delta,
            'auto_execution_rate': right_metrics.auto_execution_rate - left_metrics.auto_execution_rate,
            'block_rate': right_metrics.block_rate - left_metrics.block_rate,
            'favorable_review_rate': right_metrics.favorable_review_rate - left_metrics.favorable_review_rate,
            'safety_events_count': right_metrics.safety_events_count - left_metrics.safety_events_count,
        },
    }

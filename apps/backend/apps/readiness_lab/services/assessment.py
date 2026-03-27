from decimal import Decimal

from django.db.models import Avg

from apps.evaluation_lab.models import EvaluationMetricSet, EvaluationRun
from apps.experiment_lab.models import ExperimentRun
from apps.operator_queue.models import OperatorQueueItem
from apps.readiness_lab.models import ReadinessAssessmentRun, ReadinessStatus
from apps.readiness_lab.services.execution_readiness import summarize_execution_realism
from apps.readiness_lab.services.gates import evaluate_gates
from apps.readiness_lab.services.recommendations import build_recommendations
from apps.replay_lab.models import ReplayRun


def _to_float(value: Decimal | float | int | None, default: float = 0.0) -> float:
    if value is None:
        return default
    return float(value)


def _collect_metrics() -> dict:
    evaluation_runs = EvaluationRun.objects.filter(status='READY').select_related('metric_set')
    replay_runs = ReplayRun.objects.filter(status__in=['SUCCESS', 'PARTIAL', 'READY'])
    experiment_runs = ExperimentRun.objects.filter(status__in=['SUCCESS', 'PARTIAL'])

    metric_sets = EvaluationMetricSet.objects.filter(run__in=evaluation_runs)
    evaluation_runs_count = evaluation_runs.count()
    replay_runs_count = replay_runs.count()
    experiment_runs_count = experiment_runs.count()

    favorable_review_rate = _to_float(metric_sets.aggregate(value=Avg('favorable_review_rate'))['value'])
    block_rate = _to_float(metric_sets.aggregate(value=Avg('block_rate'))['value'])
    safety_events_total = int(metric_sets.aggregate(value=Avg('safety_events_count'))['value'] or 0)
    hard_stop_count = int(metric_sets.aggregate(value=Avg('hard_stop_count'))['value'] or 0)
    equity_delta_avg = _to_float(metric_sets.aggregate(value=Avg('equity_delta'))['value'])

    stable_runs = metric_sets.filter(
        favorable_review_rate__gte=Decimal('0.50'),
        block_rate__lte=Decimal('0.35'),
        safety_events_count__lte=2,
    ).count()

    queue_total = OperatorQueueItem.objects.count()
    queue_interventions = OperatorQueueItem.objects.filter(status__in=['APPROVED', 'REJECTED', 'SNOOZED']).count()
    operator_intervention_rate = (queue_interventions / queue_total) if queue_total else 0.0

    real_ops_experiments = experiment_runs.filter(details__market_scope='real_only').count()
    real_market_ops_coverage = (real_ops_experiments / experiment_runs_count) if experiment_runs_count else 0.0

    consistency_candidates = experiment_runs.filter(run_type='live_session_compare').count()
    consistency_hits = experiment_runs.filter(
        run_type='live_session_compare',
        normalized_metrics__consistency_band__in=['good', 'strong'],
    ).count()
    experiment_consistency_rate = (consistency_hits / consistency_candidates) if consistency_candidates else 0.0

    safety_event_rate = (safety_events_total / evaluation_runs_count) if evaluation_runs_count else 1.0
    execution_realism = summarize_execution_realism()

    return {
        'evaluation_runs_count': evaluation_runs_count,
        'replay_runs_count': replay_runs_count,
        'experiment_runs_count': experiment_runs_count,
        'favorable_review_rate': favorable_review_rate,
        'block_rate': block_rate,
        'safety_event_rate': safety_event_rate,
        'hard_stop_count': hard_stop_count,
        'max_drawdown_value': abs(min(equity_delta_avg, 0.0)),
        'stability_window_count': stable_runs,
        'operator_intervention_rate': operator_intervention_rate,
        'real_market_ops_coverage': real_market_ops_coverage,
        'experiment_consistency_rate': experiment_consistency_rate,
        'execution_realism_score': execution_realism['avg_execution_realism_score'],
        'execution_no_fill_rate': execution_realism['avg_no_fill_rate'],
        'execution_drag_avg': execution_realism['avg_execution_drag'],
        'execution_aware_replay_runs': execution_realism['execution_aware_runs'],
        'execution_readiness_penalty': execution_realism['readiness_penalty'],
        'execution_impact_summary': execution_realism,
    }


def run_readiness_assessment(profile) -> ReadinessAssessmentRun:
    metrics = _collect_metrics()
    gate_results = evaluate_gates(profile.config or {}, metrics)
    failed = [gate for gate in gate_results if not gate.passed]
    critical_failed = [gate for gate in failed if gate.severity == 'critical']
    warning_failed = [gate for gate in failed if gate.severity == 'warning']

    if critical_failed:
        status_value = ReadinessStatus.NOT_READY
    elif warning_failed:
        status_value = ReadinessStatus.CAUTION
    else:
        status_value = ReadinessStatus.READY

    pass_count = len([gate for gate in gate_results if gate.passed])
    fail_count = len(failed)
    warning_count = len(warning_failed)

    recommendations = build_recommendations(
        failed_gates=[gate.__dict__ for gate in failed],
        warning_gates=[gate.__dict__ for gate in warning_failed],
    )

    score = pass_count / len(gate_results) if gate_results else 0.0
    score = max(0.0, score - metrics.get('execution_readiness_penalty', 0.0))

    summary = f'{status_value}: {pass_count}/{len(gate_results)} gates passed.'
    rationale = ' | '.join([f"{gate.gate}: {gate.actual} {gate.comparator} {gate.expected}" for gate in failed[:4]])
    details = {
        'metrics': metrics,
        'gates': [gate.__dict__ for gate in gate_results],
        'critical_blockers': [gate.__dict__ for gate in critical_failed],
        'warnings': [gate.__dict__ for gate in warning_failed],
        'recommendations': recommendations,
        'execution_impact_summary': metrics.get('execution_impact_summary', {}),
    }

    return ReadinessAssessmentRun.objects.create(
        readiness_profile=profile,
        status=status_value,
        overall_score=Decimal(str(round(score, 4))),
        summary=summary,
        rationale=rationale,
        gates_passed_count=pass_count,
        gates_failed_count=fail_count,
        warnings_count=warning_count,
        details=details,
    )


def get_readiness_summary() -> dict:
    latest = ReadinessAssessmentRun.objects.select_related('readiness_profile').order_by('-created_at', '-id').first()
    recent = ReadinessAssessmentRun.objects.select_related('readiness_profile').order_by('-created_at', '-id')[:10]
    return {
        'latest_run': latest,
        'recent_runs': recent,
        'total_runs': ReadinessAssessmentRun.objects.count(),
        'ready_runs': ReadinessAssessmentRun.objects.filter(status=ReadinessStatus.READY).count(),
        'caution_runs': ReadinessAssessmentRun.objects.filter(status=ReadinessStatus.CAUTION).count(),
        'not_ready_runs': ReadinessAssessmentRun.objects.filter(status=ReadinessStatus.NOT_READY).count(),
    }

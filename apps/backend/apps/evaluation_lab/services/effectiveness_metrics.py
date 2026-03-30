import math
from decimal import Decimal

from apps.evaluation_lab.models import EffectivenessMetric, EffectivenessMetricStatus, EffectivenessMetricType, EvaluationSegmentScope


def _safe_rate(num: int, den: int) -> Decimal:
    if den <= 0:
        return Decimal('0.000000')
    return (Decimal(num) / Decimal(den)).quantize(Decimal('0.000001'))


def _status_for_metric(value: Decimal, *, metric_type: str, sample_count: int) -> tuple[str, str]:
    if sample_count < 5:
        return EffectivenessMetricStatus.NEEDS_MORE_DATA, 'Sample is too small for a robust interpretation.'

    if metric_type in {EffectivenessMetricType.BRIER_SCORE, EffectivenessMetricType.LOG_LOSS, EffectivenessMetricType.CALIBRATION_ERROR}:
        if value <= Decimal('0.120000'):
            return EffectivenessMetricStatus.OK, 'Calibration quality is in an acceptable zone.'
        if value <= Decimal('0.220000'):
            return EffectivenessMetricStatus.CAUTION, 'Calibration quality is drifting and should be reviewed.'
        return EffectivenessMetricStatus.POOR, 'Calibration quality is poor and likely over/under-confident.'

    if value >= Decimal('0.650000'):
        return EffectivenessMetricStatus.OK, 'Conversion/precision trend is healthy.'
    if value >= Decimal('0.450000'):
        return EffectivenessMetricStatus.CAUTION, 'Mixed effectiveness trend.'
    return EffectivenessMetricStatus.POOR, 'Low effectiveness trend requiring manual review.'


def _create_metric(*, runtime_run, metric_type: str, metric_scope: str, metric_value: Decimal, sample_count: int, reason_codes: list[str], metadata: dict) -> EffectivenessMetric:
    status, interpretation = _status_for_metric(metric_value, metric_type=metric_type, sample_count=sample_count)
    return EffectivenessMetric.objects.create(
        run=runtime_run,
        metric_type=metric_type,
        metric_scope=metric_scope,
        metric_value=metric_value,
        sample_count=sample_count,
        interpretation=interpretation,
        status=status,
        reason_codes=reason_codes,
        metadata=metadata,
    )


def build_effectiveness_metrics(*, runtime_run, outcome_records) -> list[EffectivenessMetric]:
    rows = [row for row in outcome_records if row.calibrated_probability_at_decision is not None and row.realized_result_score is not None]
    probs = [Decimal(row.calibrated_probability_at_decision) for row in rows]
    realized = [Decimal(row.realized_result_score) for row in rows]
    n = len(rows)

    metrics: list[EffectivenessMetric] = []
    if n:
        brier = (sum((p - o) ** 2 for p, o in zip(probs, realized)) / n).quantize(Decimal('0.000001'))
        log_loss = Decimal(str(sum((-(float(o) * math.log(max(float(p), 1e-6)) + (1 - float(o)) * math.log(max(1 - float(p), 1e-6)))) for p, o in zip(probs, realized)) / n)).quantize(Decimal('0.000001'))
        cal_error = (sum(abs(p - o) for p, o in zip(probs, realized)) / n).quantize(Decimal('0.000001'))
        metrics.extend(
            [
                _create_metric(runtime_run=runtime_run, metric_type=EffectivenessMetricType.BRIER_SCORE, metric_scope=EvaluationSegmentScope.GLOBAL, metric_value=brier, sample_count=n, reason_codes=['GLOBAL_CALIBRATION'], metadata={}),
                _create_metric(runtime_run=runtime_run, metric_type=EffectivenessMetricType.LOG_LOSS, metric_scope=EvaluationSegmentScope.GLOBAL, metric_value=log_loss, sample_count=n, reason_codes=['GLOBAL_CALIBRATION'], metadata={}),
                _create_metric(runtime_run=runtime_run, metric_type=EffectivenessMetricType.CALIBRATION_ERROR, metric_scope=EvaluationSegmentScope.GLOBAL, metric_value=cal_error, sample_count=n, reason_codes=['GLOBAL_CALIBRATION'], metadata={}),
            ]
        )

    approved = [r for r in outcome_records if r.risk_status_at_decision in {'APPROVED', 'APPROVED_REDUCED'}]
    blocked = [r for r in outcome_records if r.risk_status_at_decision == 'BLOCKED']
    watches = [r for r in outcome_records if r.risk_status_at_decision == 'NEEDS_REVIEW']
    proposals = [r for r in outcome_records if r.linked_paper_proposal_id is not None]
    predictions = [r for r in outcome_records if r.linked_prediction_assessment_id is not None]

    approved_hits = sum(1 for r in approved if (r.realized_result_score or Decimal('0')) >= Decimal('0.5000'))
    blocked_hits = sum(1 for r in blocked if (r.realized_result_score or Decimal('0')) >= Decimal('0.5000'))
    watch_hits = sum(1 for r in watches if (r.realized_result_score or Decimal('0')) >= Decimal('0.5000'))
    shortlist_count = sum(1 for r in outcome_records if r.linked_opportunity_assessment_id is not None)

    execution_sim_hits = sum(1 for r in proposals if bool((r.metadata or {}).get('execution_sim_recommended', False)))
    positive_edge = [r for r in outcome_records if (r.adjusted_edge_at_decision or Decimal('0')) > Decimal('0') and r.realized_result_score is not None]

    metrics.extend(
        [
            _create_metric(runtime_run=runtime_run, metric_type=EffectivenessMetricType.EDGE_CAPTURE_RATE, metric_scope=EvaluationSegmentScope.GLOBAL, metric_value=_safe_rate(sum(1 for r in positive_edge if r.realized_result_score >= Decimal('0.5000')), len(positive_edge)), sample_count=len(positive_edge), reason_codes=['EDGE_REALIZATION'], metadata={}),
            _create_metric(runtime_run=runtime_run, metric_type=EffectivenessMetricType.SHORTLIST_CONVERSION_RATE, metric_scope=EvaluationSegmentScope.GLOBAL, metric_value=_safe_rate(len(proposals), shortlist_count), sample_count=shortlist_count, reason_codes=['RESEARCH_TO_PROPOSAL'], metadata={}),
            _create_metric(runtime_run=runtime_run, metric_type=EffectivenessMetricType.PREDICTION_TO_RISK_PASS_RATE, metric_scope=EvaluationSegmentScope.GLOBAL, metric_value=_safe_rate(len(approved), len(predictions)), sample_count=len(predictions), reason_codes=['PREDICTION_TO_RISK'], metadata={}),
            _create_metric(runtime_run=runtime_run, metric_type=EffectivenessMetricType.RISK_APPROVAL_PRECISION, metric_scope=EvaluationSegmentScope.GLOBAL, metric_value=_safe_rate(approved_hits, len(approved)), sample_count=len(approved), reason_codes=['RISK_APPROVAL'], metadata={}),
            _create_metric(runtime_run=runtime_run, metric_type=EffectivenessMetricType.PROPOSAL_TO_EXECUTION_SIM_RATE, metric_scope=EvaluationSegmentScope.GLOBAL, metric_value=_safe_rate(execution_sim_hits, len(proposals)), sample_count=len(proposals), reason_codes=['PROPOSAL_TO_EXEC_SIM'], metadata={}),
            _create_metric(runtime_run=runtime_run, metric_type=EffectivenessMetricType.WATCHLIST_HIT_RATE, metric_scope=EvaluationSegmentScope.GLOBAL, metric_value=_safe_rate(watch_hits, len(watches)), sample_count=len(watches), reason_codes=['WATCHLIST_EFFICACY'], metadata={}),
            _create_metric(runtime_run=runtime_run, metric_type=EffectivenessMetricType.BLOCKED_OPPORTUNITY_ESCAPE_RATE, metric_scope=EvaluationSegmentScope.GLOBAL, metric_value=_safe_rate(blocked_hits, len(blocked)), sample_count=len(blocked), reason_codes=['BLOCKED_ESCAPE'], metadata={}),
        ]
    )

    global_hit_rate = _safe_rate(sum(1 for r in outcome_records if (r.realized_result_score or Decimal('0')) >= Decimal('0.5000')), len(outcome_records))
    for scope, metric_type in [
        ('provider', EffectivenessMetricType.PROVIDER_BIAS_INDICATOR),
        ('category', EffectivenessMetricType.CATEGORY_BIAS_INDICATOR),
        ('model_mode', EffectivenessMetricType.MODEL_MODE_DRIFT_INDICATOR),
    ]:
        for value in sorted({(r.metadata or {}).get(scope, 'unknown') for r in outcome_records}):
            scoped = [r for r in outcome_records if (r.metadata or {}).get(scope, 'unknown') == value]
            scoped_hit_rate = _safe_rate(sum(1 for r in scoped if (r.realized_result_score or Decimal('0')) >= Decimal('0.5000')), len(scoped))
            gap = abs(scoped_hit_rate - global_hit_rate).quantize(Decimal('0.000001'))
            metrics.append(
                _create_metric(
                    runtime_run=runtime_run,
                    metric_type=metric_type,
                    metric_scope=scope,
                    metric_value=gap,
                    sample_count=len(scoped),
                    reason_codes=[f'{scope.upper()}_DEVIATION'],
                    metadata={'segment_value': value, 'segment_hit_rate': str(scoped_hit_rate), 'global_hit_rate': str(global_hit_rate)},
                )
            )

    return metrics

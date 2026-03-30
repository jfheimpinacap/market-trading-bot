from __future__ import annotations

from decimal import Decimal

from apps.evaluation_lab.models import EffectivenessMetric, EffectivenessMetricStatus, EffectivenessMetricType, EvaluationRuntimeRun
from apps.opportunity_supervisor.models import OpportunityFusionAssessment
from apps.risk_agent.models import RiskApprovalDecision, RiskRuntimeApprovalStatus


def _d(value: Decimal | float | int | str | None, default: str = '0') -> Decimal:
    if value is None:
        return Decimal(default)
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def gather_recent_signals(*, target_component: str, target_scope: str) -> dict:
    latest_eval = EvaluationRuntimeRun.objects.order_by('-started_at', '-id').first()
    latest_eval_metrics = (
        EffectivenessMetric.objects.filter(run=latest_eval).order_by('-created_at', '-id') if latest_eval else EffectivenessMetric.objects.none()
    )

    calibration_metric = latest_eval_metrics.filter(metric_type=EffectivenessMetricType.CALIBRATION_ERROR).first()
    risk_precision_metric = latest_eval_metrics.filter(metric_type=EffectivenessMetricType.RISK_APPROVAL_PRECISION).first()
    shortlist_metric = latest_eval_metrics.filter(metric_type=EffectivenessMetricType.SHORTLIST_CONVERSION_RATE).first()
    provider_bias_metric = latest_eval_metrics.filter(metric_type=EffectivenessMetricType.PROVIDER_BIAS_INDICATOR).first()
    category_bias_metric = latest_eval_metrics.filter(metric_type=EffectivenessMetricType.CATEGORY_BIAS_INDICATOR).first()
    drift_metric = latest_eval_metrics.filter(metric_type=EffectivenessMetricType.MODEL_MODE_DRIFT_INDICATOR).first()

    recent_risk_decisions = RiskApprovalDecision.objects.order_by('-created_at', '-id')[:100]
    risk_block_rate = Decimal('0')
    watch_ratio = Decimal('0')
    risk_count = len(recent_risk_decisions)
    if risk_count:
        blocked = sum(
            1
            for item in recent_risk_decisions
            if item.approval_status in {RiskRuntimeApprovalStatus.BLOCKED, RiskRuntimeApprovalStatus.NEEDS_REVIEW}
        )
        watch = sum(1 for item in recent_risk_decisions if item.watch_required)
        risk_block_rate = Decimal(blocked) / Decimal(risk_count)
        watch_ratio = Decimal(watch) / Decimal(risk_count)

    recent_opportunity = OpportunityFusionAssessment.objects.order_by('-created_at', '-id')[:100]
    opp_quality = Decimal('0')
    opp_count = len(recent_opportunity)
    if opp_count:
        opp_quality = sum((_d(item.final_opportunity_score) for item in recent_opportunity), Decimal('0')) / Decimal(opp_count)

    return {
        'target_component': target_component,
        'target_scope': target_scope,
        'latest_evaluation_runtime_run_id': latest_eval.id if latest_eval else None,
        'calibration_error': _d(getattr(calibration_metric, 'metric_value', None)),
        'calibration_status': getattr(calibration_metric, 'status', EffectivenessMetricStatus.NEEDS_MORE_DATA),
        'risk_precision': _d(getattr(risk_precision_metric, 'metric_value', None)),
        'risk_precision_status': getattr(risk_precision_metric, 'status', EffectivenessMetricStatus.NEEDS_MORE_DATA),
        'shortlist_quality': _d(getattr(shortlist_metric, 'metric_value', None)),
        'provider_bias': _d(getattr(provider_bias_metric, 'metric_value', None)),
        'category_bias': _d(getattr(category_bias_metric, 'metric_value', None)),
        'drift_indicator': _d(getattr(drift_metric, 'metric_value', None)),
        'drift_status': getattr(drift_metric, 'status', EffectivenessMetricStatus.NEEDS_MORE_DATA),
        'risk_block_rate': risk_block_rate,
        'watch_ratio': watch_ratio,
        'opportunity_quality': opp_quality,
        'opportunity_sample_count': opp_count,
        'risk_sample_count': risk_count,
    }

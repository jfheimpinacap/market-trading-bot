from __future__ import annotations

from decimal import Decimal

from apps.evaluation_lab.models import EffectivenessMetric, EffectivenessMetricType
from apps.experiment_lab.models import ChampionChallengerComparisonStatus, ExperimentCandidate

MIN_SAMPLE_COUNT = 30


def _d(value: object) -> Decimal:
    return Decimal(str(value or '0'))


def _metric_delta(metric: EffectivenessMetric | None) -> Decimal:
    if metric is None:
        return Decimal('0')
    baseline = _d(metric.metadata.get('baseline_value') if metric.metadata else 0)
    return _d(metric.metric_value) - baseline


def build_comparison_for_candidate(*, candidate: ExperimentCandidate, baseline_label: str, challenger_label: str) -> dict:
    proposal = candidate.linked_tuning_proposal
    metric = proposal.source_metric
    sample_count = int(metric.sample_count if metric else 0)

    compared_metrics = {
        'calibration_error_delta': str(_metric_delta(metric) if metric and metric.metric_type == EffectivenessMetricType.CALIBRATION_ERROR else Decimal('0')),
        'brier_delta': str(_metric_delta(metric) if metric and metric.metric_type == EffectivenessMetricType.BRIER_SCORE else Decimal('0')),
        'log_loss_delta': str(_metric_delta(metric) if metric and metric.metric_type == EffectivenessMetricType.LOG_LOSS else Decimal('0')),
        'risk_precision_delta': str(_metric_delta(metric) if metric and metric.metric_type == EffectivenessMetricType.RISK_APPROVAL_PRECISION else Decimal('0')),
        'shortlist_conversion_delta': str(_metric_delta(metric) if metric and metric.metric_type == EffectivenessMetricType.SHORTLIST_CONVERSION_RATE else Decimal('0')),
        'opportunity_score_delta': str(_metric_delta(metric) if metric and metric.metric_type == EffectivenessMetricType.EDGE_CAPTURE_RATE else Decimal('0')),
        'execution_realism_delta': str(_d((proposal.metadata or {}).get('execution_realism_delta'))),
    }

    risk_precision_delta = _d(compared_metrics['risk_precision_delta'])
    calibration_delta = _d(compared_metrics['calibration_error_delta'])
    brier_delta = _d(compared_metrics['brier_delta'])
    log_loss_delta = _d(compared_metrics['log_loss_delta'])

    improvement_votes = sum(1 for value in [calibration_delta, brier_delta, log_loss_delta] if value < 0) + (1 if risk_precision_delta > 0 else 0)
    degradation_votes = sum(1 for value in [calibration_delta, brier_delta, log_loss_delta] if value > 0) + (1 if risk_precision_delta < 0 else 0)

    reason_codes: list[str] = []
    if sample_count < MIN_SAMPLE_COUNT:
        reason_codes.append('sample_count_below_threshold')
        status = ChampionChallengerComparisonStatus.NEEDS_MORE_DATA
        rationale = 'Comparison is not reliable yet because sample count is below threshold.'
    elif improvement_votes > 0 and degradation_votes == 0:
        status = ChampionChallengerComparisonStatus.IMPROVED
        rationale = 'Challenger improves relevant metrics without material degradations.'
        reason_codes.append('positive_delta_cluster')
    elif degradation_votes > 0 and improvement_votes == 0:
        status = ChampionChallengerComparisonStatus.DEGRADED
        rationale = 'Challenger degrades key metrics against baseline.'
        reason_codes.append('negative_delta_cluster')
    elif improvement_votes > 0 and degradation_votes > 0:
        status = ChampionChallengerComparisonStatus.MIXED
        rationale = 'Challenger improves some metrics but degrades others.'
        reason_codes.append('mixed_signal')
    else:
        status = ChampionChallengerComparisonStatus.INCONCLUSIVE
        rationale = 'No meaningful delta was detected between baseline and challenger.'
        reason_codes.append('flat_deltas')

    confidence = Decimal('0.35')
    if sample_count >= 100:
        confidence = Decimal('0.80')
    elif sample_count >= 50:
        confidence = Decimal('0.60')

    return {
        'linked_candidate': candidate,
        'baseline_label': baseline_label,
        'challenger_label': challenger_label,
        'comparison_status': status,
        'compared_metrics': compared_metrics,
        'sample_count': sample_count,
        'confidence_score': confidence,
        'rationale': rationale,
        'reason_codes': reason_codes,
        'metadata': {
            'source_metric_id': metric.id if metric else None,
            'source_metric_type': metric.metric_type if metric else None,
            'paper_only': True,
            'runtime_mutation_applied': False,
        },
    }

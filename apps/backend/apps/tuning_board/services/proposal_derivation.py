from decimal import Decimal

from apps.evaluation_lab.models import EffectivenessMetricStatus, EffectivenessMetricType, EvaluationRecommendation, EvaluationRuntimeRun
from apps.tuning_board.models import TuningComponent, TuningProposalStatus, TuningProposalType, TuningScope


def derive_tuning_candidates(evaluation_run: EvaluationRuntimeRun) -> list[dict]:
    candidates: list[dict] = []

    for metric in evaluation_run.effectiveness_metrics.all():
        if metric.status not in [EffectivenessMetricStatus.POOR, EffectivenessMetricStatus.CAUTION, EffectivenessMetricStatus.NEEDS_MORE_DATA]:
            continue

        scope = metric.metric_scope or TuningScope.GLOBAL
        target_value = (metric.metadata or {}).get('segment_value', '')

        if metric.metric_type == EffectivenessMetricType.CALIBRATION_ERROR:
            candidates.append(
                {
                    'proposal_type': TuningProposalType.CALIBRATION_BIAS_OFFSET,
                    'target_component': TuningComponent.CALIBRATION,
                    'target_scope': scope,
                    'target_value': target_value,
                    'current_value': metric.metric_value,
                    'proposed_value': None,
                    'source_metric': metric,
                    'rationale': 'Calibration error exceeded expected tolerance and requires manual offset review.',
                    'reason_codes': ['HIGH_CALIBRATION_GAP'],
                }
            )
        elif metric.metric_type == EffectivenessMetricType.RISK_APPROVAL_PRECISION:
            candidates.append(
                {
                    'proposal_type': TuningProposalType.RISK_GATE_THRESHOLD,
                    'target_component': TuningComponent.RISK,
                    'target_scope': scope,
                    'target_value': target_value,
                    'current_value': metric.metric_value,
                    'proposed_value': None,
                    'source_metric': metric,
                    'rationale': 'Risk approval precision degraded and indicates gate threshold review.',
                    'reason_codes': ['RISK_PRECISION_DEGRADED'],
                }
            )
        elif metric.metric_type == EffectivenessMetricType.BLOCKED_OPPORTUNITY_ESCAPE_RATE:
            candidates.append(
                {
                    'proposal_type': TuningProposalType.RISK_GATE_THRESHOLD,
                    'target_component': TuningComponent.RISK,
                    'target_scope': scope,
                    'target_value': target_value,
                    'current_value': metric.metric_value,
                    'proposed_value': None,
                    'source_metric': metric,
                    'rationale': 'Blocked opportunity escape rate is elevated; verify whether gate is too strict.',
                    'reason_codes': ['BLOCKED_ESCAPE_HIGH'],
                }
            )
        elif metric.metric_type == EffectivenessMetricType.SHORTLIST_CONVERSION_RATE:
            candidates.append(
                {
                    'proposal_type': TuningProposalType.SHORTLIST_THRESHOLD,
                    'target_component': TuningComponent.RESEARCH,
                    'target_scope': scope,
                    'target_value': target_value,
                    'current_value': metric.metric_value,
                    'proposed_value': None,
                    'source_metric': metric,
                    'rationale': 'Shortlist conversion underperformed and needs conservative shortlist threshold review.',
                    'reason_codes': ['SHORTLIST_CONVERSION_LOW'],
                }
            )

        if metric.status == EffectivenessMetricStatus.NEEDS_MORE_DATA:
            candidates[-1]['proposal_status'] = TuningProposalStatus.WATCH
            candidates[-1]['reason_codes'].append('LOW_SAMPLE')

    recommendations = evaluation_run.recommendations.select_related('target_metric')
    for recommendation in recommendations:
        mapped = _from_evaluation_recommendation(recommendation)
        if mapped:
            candidates.append(mapped)

    return candidates


def _from_evaluation_recommendation(recommendation: EvaluationRecommendation) -> dict | None:
    recommendation_type = recommendation.recommendation_type
    base = {
        'target_scope': TuningScope.GLOBAL,
        'target_value': '',
        'current_value': None,
        'proposed_value': None,
        'source_metric': recommendation.target_metric,
        'source_recommendation': recommendation,
        'reason_codes': list(recommendation.reason_codes or []),
        'rationale': recommendation.rationale,
    }

    if recommendation_type == 'REVIEW_CALIBRATION_DRIFT':
        return {**base, 'proposal_type': TuningProposalType.CALIBRATION_BIAS_OFFSET, 'target_component': TuningComponent.CALIBRATION}
    if recommendation_type == 'TIGHTEN_RISK_GATE':
        return {**base, 'proposal_type': TuningProposalType.RISK_GATE_THRESHOLD, 'target_component': TuningComponent.RISK}
    if recommendation_type == 'RELAX_RISK_GATE':
        return {**base, 'proposal_type': TuningProposalType.RISK_GATE_THRESHOLD, 'target_component': TuningComponent.RISK}
    if recommendation_type == 'REVIEW_PROVIDER_BIAS':
        return {
            **base,
            'proposal_type': TuningProposalType.PREDICTION_CONFIDENCE_THRESHOLD,
            'target_component': TuningComponent.PREDICTION,
            'target_scope': TuningScope.PROVIDER,
        }
    if recommendation_type == 'REVIEW_CATEGORY_BIAS':
        return {
            **base,
            'proposal_type': TuningProposalType.PREDICTION_EDGE_THRESHOLD,
            'target_component': TuningComponent.PREDICTION,
            'target_scope': TuningScope.CATEGORY,
        }
    if recommendation_type == 'REQUIRE_MORE_DATA':
        return {
            **base,
            'proposal_type': TuningProposalType.MANUAL_REVIEW_RULE,
            'target_component': TuningComponent.LEARNING,
            'proposal_status': TuningProposalStatus.WATCH,
            'reason_codes': [*base['reason_codes'], 'LOW_SAMPLE'],
            'proposed_value': Decimal('0'),
        }
    return None

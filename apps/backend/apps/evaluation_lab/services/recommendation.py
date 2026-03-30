from decimal import Decimal

from apps.evaluation_lab.models import (
    EffectivenessMetricStatus,
    EffectivenessMetricType,
    EvaluationRecommendation,
    EvaluationRecommendationType,
)


def build_recommendations(*, runtime_run, metrics, drift_flags) -> list[EvaluationRecommendation]:
    recommendations: list[EvaluationRecommendation] = []

    poor_metrics = [m for m in metrics if m.status == EffectivenessMetricStatus.POOR]
    if poor_metrics:
        recommendations.append(
            EvaluationRecommendation.objects.create(
                run=runtime_run,
                recommendation_type=EvaluationRecommendationType.INCREASE_MANUAL_REVIEW,
                rationale='Multiple metrics are marked POOR; increase manual review before paper proposals.',
                reason_codes=['POOR_METRIC_CLUSTER'],
                confidence=Decimal('0.8200'),
                blockers=[],
            )
        )

    for flag in drift_flags:
        recommendation_type = EvaluationRecommendationType.REVIEW_CALIBRATION_DRIFT
        if flag['flag_type'] == EffectivenessMetricType.PROVIDER_BIAS_INDICATOR.upper():
            recommendation_type = EvaluationRecommendationType.REVIEW_PROVIDER_BIAS
        elif flag['flag_type'] == EffectivenessMetricType.CATEGORY_BIAS_INDICATOR.upper():
            recommendation_type = EvaluationRecommendationType.REVIEW_CATEGORY_BIAS
        elif flag['flag_type'] == EffectivenessMetricType.MODEL_MODE_DRIFT_INDICATOR.upper():
            recommendation_type = EvaluationRecommendationType.MONITOR_MODEL_MODE

        recommendations.append(
            EvaluationRecommendation.objects.create(
                run=runtime_run,
                recommendation_type=recommendation_type,
                rationale=flag['reason'],
                reason_codes=[flag['flag_type'], f"SCOPE_{flag['scope'].upper()}"],
                confidence=Decimal('0.7600'),
                blockers=[],
                metadata={'segment_value': flag.get('segment_value', 'unknown')},
            )
        )

    blocked_escape = next((m for m in metrics if m.metric_type == EffectivenessMetricType.BLOCKED_OPPORTUNITY_ESCAPE_RATE and m.metric_scope == 'global'), None)
    approval_precision = next((m for m in metrics if m.metric_type == EffectivenessMetricType.RISK_APPROVAL_PRECISION and m.metric_scope == 'global'), None)

    if blocked_escape and blocked_escape.sample_count >= 5 and blocked_escape.metric_value >= Decimal('0.550000'):
        recommendations.append(
            EvaluationRecommendation.objects.create(
                run=runtime_run,
                target_metric=blocked_escape,
                recommendation_type=EvaluationRecommendationType.RELAX_RISK_GATE,
                rationale='Blocked opportunities are frequently resolving positively; review conservative risk gating.',
                reason_codes=['BLOCKED_ESCAPE_HIGH'],
                confidence=Decimal('0.7000'),
                blockers=['Requires human threshold review; no auto policy changes.'],
            )
        )

    if approval_precision and approval_precision.sample_count >= 5 and approval_precision.metric_value <= Decimal('0.450000'):
        recommendations.append(
            EvaluationRecommendation.objects.create(
                run=runtime_run,
                target_metric=approval_precision,
                recommendation_type=EvaluationRecommendationType.TIGHTEN_RISK_GATE,
                rationale='Approved opportunities underperform ex-post; tighten risk gate manually.',
                reason_codes=['APPROVAL_PRECISION_LOW'],
                confidence=Decimal('0.7300'),
                blockers=['Requires operator sign-off; no auto threshold tuning.'],
            )
        )

    needs_more_data_count = sum(1 for m in metrics if m.status == EffectivenessMetricStatus.NEEDS_MORE_DATA)
    if needs_more_data_count >= 3:
        recommendations.append(
            EvaluationRecommendation.objects.create(
                run=runtime_run,
                recommendation_type=EvaluationRecommendationType.REQUIRE_MORE_DATA,
                rationale='Several metrics have low sample size; collect more resolved outcomes before policy updates.',
                reason_codes=['LOW_SAMPLE_SIZE'],
                confidence=Decimal('0.9000'),
                blockers=[],
            )
        )

    return recommendations

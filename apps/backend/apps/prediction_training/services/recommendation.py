from __future__ import annotations

from apps.prediction_training.models import ActiveModelRecommendationCode, ModelComparisonRun
from apps.prediction_training.services.evaluation import EvaluationProfileConfig


def build_recommendation(*, comparison_run: ModelComparisonRun, profile: EvaluationProfileConfig) -> ModelComparisonRun:
    baseline = (comparison_run.details or {}).get('baseline_metrics', {})
    candidate = (comparison_run.details or {}).get('candidate_metrics', {})
    cfg = profile.config or {}
    min_coverage = float(cfg.get('minimum_coverage', 0.6))
    max_failure_ratio = float(cfg.get('max_failures_ratio', 0.1))
    min_delta = float(cfg.get('activation_min_score_delta', 0.03))
    score_delta = float((comparison_run.metrics_summary or {}).get('score_delta', 0.0))

    reasons: list[str] = []

    candidate_coverage = float(candidate.get('coverage', 0.0))
    candidate_failures = float(candidate.get('failure_count', 0))
    rows = max(float((comparison_run.metrics_summary or {}).get('rows_evaluated', 0)), 1.0)
    failure_ratio = candidate_failures / rows

    if candidate_coverage < min_coverage:
        reasons.append('insufficient coverage')
    if failure_ratio > max_failure_ratio:
        reasons.append('failure rate too high')
    if float(candidate.get('calibration_error', 1.0)) > float(baseline.get('calibration_error', 1.0)):
        reasons.append('worse calibration than baseline')

    winner = 'INCONCLUSIVE'
    if score_delta > min_delta:
        winner = 'CANDIDATE_BETTER'
    elif score_delta < -min_delta:
        winner = 'BASELINE_BETTER'

    if reasons:
        recommendation = ActiveModelRecommendationCode.CAUTION_REVIEW_MANUALLY
    elif winner == 'CANDIDATE_BETTER':
        recommendation = ActiveModelRecommendationCode.ACTIVATE_CANDIDATE
        reasons.append('candidate outperforms baseline')
    elif winner == 'BASELINE_BETTER':
        if comparison_run.baseline_key == 'heuristic_baseline':
            recommendation = ActiveModelRecommendationCode.KEEP_HEURISTIC
            reasons.append('baseline heuristic remains stronger')
        else:
            recommendation = ActiveModelRecommendationCode.KEEP_ACTIVE_MODEL
            reasons.append('active baseline remains stronger')
    else:
        recommendation = ActiveModelRecommendationCode.CAUTION_REVIEW_MANUALLY
        reasons.append('metrics are inconclusive')

    comparison_run.winner = winner
    comparison_run.recommendation_code = recommendation
    comparison_run.recommendation_reasons = reasons
    comparison_run.save(update_fields=['winner', 'recommendation_code', 'recommendation_reasons', 'updated_at'])
    return comparison_run

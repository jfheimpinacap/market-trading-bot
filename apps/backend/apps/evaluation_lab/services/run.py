from collections import Counter

from django.utils import timezone

from apps.evaluation_lab.models import EvaluationRuntimeRun
from apps.evaluation_lab.services.calibration_metrics import build_calibration_buckets
from apps.evaluation_lab.services.drift_detection import detect_drift_flags
from apps.evaluation_lab.services.effectiveness_metrics import build_effectiveness_metrics
from apps.evaluation_lab.services.outcome_linking import build_outcome_alignment_records
from apps.evaluation_lab.services.recommendation import build_recommendations


def run_runtime_evaluation() -> EvaluationRuntimeRun:
    runtime_run = EvaluationRuntimeRun.objects.create(started_at=timezone.now(), metadata={'manual_first': True, 'mode': 'paper_only'})

    records = build_outcome_alignment_records(runtime_run=runtime_run)
    buckets = build_calibration_buckets(runtime_run=runtime_run, outcome_records=records)
    metrics = build_effectiveness_metrics(runtime_run=runtime_run, outcome_records=records)
    drift_flags = detect_drift_flags(metrics=metrics, buckets=buckets)
    recommendations = build_recommendations(runtime_run=runtime_run, metrics=metrics, drift_flags=drift_flags)

    rec_counter = Counter(rec.recommendation_type for rec in recommendations)

    runtime_run.resolved_market_count = len(records)
    runtime_run.linked_prediction_count = sum(1 for row in records if row.linked_prediction_assessment_id)
    runtime_run.linked_risk_count = sum(1 for row in records if row.linked_risk_approval_id)
    runtime_run.linked_proposal_count = sum(1 for row in records if row.linked_paper_proposal_id)
    runtime_run.calibration_bucket_count = len(buckets)
    runtime_run.metric_count = len(metrics)
    runtime_run.drift_flag_count = len(drift_flags)
    runtime_run.recommendation_summary = dict(rec_counter)
    runtime_run.completed_at = timezone.now()
    runtime_run.metadata = {
        **(runtime_run.metadata or {}),
        'drift_flags': drift_flags,
    }
    runtime_run.save()

    return runtime_run


def build_runtime_summary() -> dict:
    latest = EvaluationRuntimeRun.objects.order_by('-started_at', '-id').first()
    if latest is None:
        return {
            'latest_run': None,
            'manual_review_required': False,
            'poor_metric_count': 0,
            'drift_flags': [],
        }

    poor_metric_count = latest.effectiveness_metrics.filter(status='POOR').count()
    recommendations = latest.recommendations.order_by('-created_at', '-id')[:10]
    return {
        'latest_run': latest,
        'manual_review_required': poor_metric_count > 0 or latest.drift_flag_count > 0,
        'poor_metric_count': poor_metric_count,
        'drift_flags': (latest.metadata or {}).get('drift_flags', []),
        'recommendations': recommendations,
    }

from __future__ import annotations

from apps.prediction_training.models import ModelComparisonRun
from apps.prediction_training.services.registry import get_active_model_artifact


def governance_summary() -> dict:
    latest_run = ModelComparisonRun.objects.select_related('evaluation_profile').prefetch_related('results').order_by('-created_at', '-id').first()
    active_model = get_active_model_artifact()
    return {
        'active_model': {
            'id': active_model.id,
            'name': active_model.name,
            'version': active_model.version,
            'model_type': active_model.model_type,
        }
        if active_model
        else None,
        'latest_comparison': {
            'id': latest_run.id,
            'status': latest_run.status,
            'scope': latest_run.scope,
            'baseline_key': latest_run.baseline_key,
            'candidate_key': latest_run.candidate_key,
            'winner': latest_run.winner,
            'recommendation_code': latest_run.recommendation_code,
            'recommendation_reasons': latest_run.recommendation_reasons,
            'metrics_summary': latest_run.metrics_summary,
            'created_at': latest_run.created_at,
        }
        if latest_run
        else None,
        'recent_recommendations': [
            {
                'id': item.id,
                'winner': item.winner,
                'recommendation_code': item.recommendation_code,
                'created_at': item.created_at,
            }
            for item in ModelComparisonRun.objects.order_by('-created_at', '-id')[:10]
        ],
    }

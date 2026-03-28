from django.db.models import Count

from apps.autonomy_scenario.models import AutonomyScenarioRun, ScenarioRecommendation


def list_runs_queryset():
    return AutonomyScenarioRun.objects.prefetch_related('options', 'risk_estimates', 'recommendations').order_by('-created_at', '-id')


def list_recommendations_queryset():
    return ScenarioRecommendation.objects.select_related('run', 'option').order_by('-score', '-created_at', '-id')


def build_summary_payload() -> dict:
    latest_run = list_runs_queryset().first()
    recommendation_breakdown = ScenarioRecommendation.objects.values('recommendation_code').annotate(total=Count('id')).order_by('-total')
    return {
        'total_runs': AutonomyScenarioRun.objects.count(),
        'latest_run_id': latest_run.id if latest_run else None,
        'latest_summary': latest_run.summary if latest_run else None,
        'latest_selected_option_key': latest_run.selected_option_key if latest_run else None,
        'latest_recommendation_code': latest_run.selected_recommendation_code if latest_run else None,
        'recommendation_breakdown': {row['recommendation_code']: row['total'] for row in recommendation_breakdown},
    }

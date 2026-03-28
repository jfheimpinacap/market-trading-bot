from django.db.models import Count

from apps.trust_calibration.models import AutomationFeedbackSnapshot, TrustCalibrationRecommendation, TrustCalibrationRun


def build_summary_payload() -> dict:
    latest_run = TrustCalibrationRun.objects.order_by('-started_at', '-id').first()
    feedback_qs = AutomationFeedbackSnapshot.objects
    recommendations_qs = TrustCalibrationRecommendation.objects
    if latest_run:
        feedback_qs = feedback_qs.filter(run=latest_run)
        recommendations_qs = recommendations_qs.filter(run=latest_run)

    action_rows = list(feedback_qs.values('action_type', 'metrics', 'current_trust_tier'))
    friction_values = [float((item.get('metrics') or {}).get('approval_friction_score') or 0) for item in action_rows]
    avg_friction = sum(friction_values) / len(friction_values) if friction_values else 0

    auto_success_domains = sorted(action_rows, key=lambda item: float((item.get('metrics') or {}).get('auto_execution_success_rate') or 0), reverse=True)[:3]
    caution_domains = sorted(action_rows, key=lambda item: float((item.get('metrics') or {}).get('auto_action_followed_by_incident_rate') or 0), reverse=True)[:3]

    breakdown_rows = recommendations_qs.values('recommendation_type').annotate(count=Count('id'))
    return {
        'latest_run': latest_run.id if latest_run else None,
        'actions_analyzed': feedback_qs.count(),
        'avg_approval_friction': f'{avg_friction:.4f}',
        'recommendations_count': recommendations_qs.count(),
        'recommendation_breakdown': {row['recommendation_type']: row['count'] for row in breakdown_rows},
        'top_auto_success_domains': auto_success_domains,
        'top_caution_domains': caution_domains,
    }

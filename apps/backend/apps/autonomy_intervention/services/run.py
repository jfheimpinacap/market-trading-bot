from __future__ import annotations

from collections import Counter
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from apps.autonomy_campaign.models import AutonomyCampaign
from apps.autonomy_intervention.models import CampaignInterventionRequest, InterventionRun


def generate_intervention_summary(*, actor: str = 'operator-ui'):
    now = timezone.now()
    active_campaign_count = AutonomyCampaign.objects.filter(status__in=['RUNNING', 'PAUSED', 'BLOCKED']).count()
    open_request_count = CampaignInterventionRequest.objects.filter(request_status='OPEN').count()
    approval_required_count = CampaignInterventionRequest.objects.filter(request_status='APPROVAL_REQUIRED').count()
    ready_request_count = CampaignInterventionRequest.objects.filter(request_status='READY').count()
    blocked_request_count = CampaignInterventionRequest.objects.filter(request_status='BLOCKED').count()
    executed_recent_count = CampaignInterventionRequest.objects.filter(request_status='EXECUTED', updated_at__gte=now - timedelta(hours=24)).count()
    recommendation_summary = Counter(CampaignInterventionRequest.objects.values_list('requested_action', flat=True))

    run = InterventionRun.objects.create(
        active_campaign_count=active_campaign_count,
        open_request_count=open_request_count,
        approval_required_count=approval_required_count,
        ready_request_count=ready_request_count,
        blocked_request_count=blocked_request_count,
        executed_recent_count=executed_recent_count,
        recommendation_summary=dict(recommendation_summary),
        metadata={'actor': actor},
    )
    return run


def build_summary_payload():
    latest = InterventionRun.objects.order_by('-created_at', '-id').first()
    if not latest:
        latest = generate_intervention_summary()
    campaigns_needing = CampaignInterventionRequest.objects.filter(
        request_status__in=['OPEN', 'APPROVAL_REQUIRED', 'READY', 'BLOCKED']
    ).values_list('campaign_id', flat=True).distinct().count()
    return {
        'latest_run_id': latest.id,
        'active_campaign_count': latest.active_campaign_count,
        'open_request_count': latest.open_request_count,
        'approval_required_count': latest.approval_required_count,
        'ready_request_count': latest.ready_request_count,
        'blocked_request_count': latest.blocked_request_count,
        'executed_recent_count': latest.executed_recent_count,
        'campaigns_needing_intervention': campaigns_needing,
        'recommendation_summary': latest.recommendation_summary,
    }

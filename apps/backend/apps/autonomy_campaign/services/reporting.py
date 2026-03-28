from django.db.models import Count

from apps.autonomy_campaign.models import AutonomyCampaign


def list_campaigns_queryset():
    return AutonomyCampaign.objects.prefetch_related('steps__domain', 'checkpoints').order_by('-created_at', '-id')


def build_summary_payload() -> dict:
    latest = list_campaigns_queryset().first()
    status_breakdown = AutonomyCampaign.objects.values('status').annotate(total=Count('id')).order_by('-total')
    return {
        'total_campaigns': AutonomyCampaign.objects.count(),
        'active_campaigns': AutonomyCampaign.objects.filter(status__in=['RUNNING', 'BLOCKED', 'PAUSED']).count(),
        'latest_campaign_id': latest.id if latest else None,
        'latest_status': latest.status if latest else None,
        'latest_source_type': latest.source_type if latest else None,
        'status_breakdown': {row['status']: row['total'] for row in status_breakdown},
    }

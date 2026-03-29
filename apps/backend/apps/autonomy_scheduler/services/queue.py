from django.utils import timezone

from apps.autonomy_campaign.models import AutonomyCampaign, AutonomyCampaignStatus
from apps.autonomy_scheduler.models import CampaignAdmission, CampaignAdmissionSourceType, CampaignAdmissionStatus


ELIGIBLE_STATUSES = [AutonomyCampaignStatus.DRAFT, AutonomyCampaignStatus.READY, AutonomyCampaignStatus.PAUSED, AutonomyCampaignStatus.BLOCKED]


def ensure_campaign_admissions() -> list[CampaignAdmission]:
    for campaign in AutonomyCampaign.objects.filter(status__in=ELIGIBLE_STATUSES):
        source_type = campaign.source_type if campaign.source_type in CampaignAdmissionSourceType.values else CampaignAdmissionSourceType.MANUAL
        CampaignAdmission.objects.get_or_create(
            campaign=campaign,
            defaults={
                'status': CampaignAdmissionStatus.PENDING,
                'source_type': source_type,
                'metadata': {'created_by': 'autonomy_scheduler.queue', 'created_at': timezone.now().isoformat()},
            },
        )
    return list(CampaignAdmission.objects.select_related('campaign', 'requested_window').all())


def queue_counts(rows: list[CampaignAdmission]) -> dict:
    counts = {status: 0 for status in CampaignAdmissionStatus.values}
    for row in rows:
        counts[row.status] = counts.get(row.status, 0) + 1
    return counts

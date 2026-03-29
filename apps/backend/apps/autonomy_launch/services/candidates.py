from apps.autonomy_campaign.models import AutonomyCampaign
from apps.autonomy_scheduler.models import CampaignAdmission, CampaignAdmissionStatus


def list_launch_candidates():
    admissions = (
        CampaignAdmission.objects.select_related('campaign')
        .filter(status__in=[CampaignAdmissionStatus.ADMITTED, CampaignAdmissionStatus.READY])
        .order_by('-priority_score', '-readiness_score', 'created_at')
    )
    return [admission for admission in admissions if admission.campaign.status in ['READY', 'PAUSED']]


def candidate_campaigns() -> list[AutonomyCampaign]:
    return [admission.campaign for admission in list_launch_candidates()]

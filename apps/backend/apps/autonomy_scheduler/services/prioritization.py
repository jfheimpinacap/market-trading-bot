from apps.autonomy_campaign.models import AutonomyCampaignStep
from apps.autonomy_scheduler.models import CampaignAdmission


def score_admission(admission: CampaignAdmission) -> CampaignAdmission:
    campaign = admission.campaign
    metadata = campaign.metadata or {}
    suggested_priority = int(metadata.get('priority_score', 0) or 0)
    suggested_readiness = int(metadata.get('readiness_score', 0) or 0)
    open_steps = AutonomyCampaignStep.objects.filter(campaign=campaign, status__in=['READY', 'PENDING']).count()
    blocked_steps = AutonomyCampaignStep.objects.filter(campaign=campaign, status='WAITING_APPROVAL').count()
    admission.priority_score = max(0, min(100, suggested_priority + min(30, campaign.total_steps)))
    admission.readiness_score = max(0, min(100, suggested_readiness + max(0, 40 - open_steps * 5) - blocked_steps * 10))
    admission.save(update_fields=['priority_score', 'readiness_score', 'updated_at'])
    return admission


def prioritize(rows: list[CampaignAdmission]) -> list[CampaignAdmission]:
    scored = [score_admission(row) for row in rows]
    return sorted(scored, key=lambda item: (item.status != 'READY', -item.priority_score, -item.readiness_score, item.created_at))

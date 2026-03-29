from django.db import transaction
from django.utils import timezone

from apps.approval_center.models import ApprovalPriority, ApprovalRequest, ApprovalRequestStatus, ApprovalSourceType
from apps.autonomy_scheduler.models import CampaignAdmission, CampaignAdmissionStatus


@transaction.atomic
def admit_campaign(*, campaign_id: int, actor: str = 'operator-ui') -> CampaignAdmission:
    admission = CampaignAdmission.objects.select_related('campaign').get(campaign_id=campaign_id)
    if admission.status not in [CampaignAdmissionStatus.READY, CampaignAdmissionStatus.PENDING, CampaignAdmissionStatus.DEFERRED]:
        return admission

    campaign = admission.campaign
    requires_approval = admission.priority_score >= 80
    if requires_approval:
        ApprovalRequest.objects.update_or_create(
            source_type=ApprovalSourceType.OTHER,
            source_object_id=f'autonomy_scheduler:admit:{campaign.id}',
            defaults={
                'title': f'Approval required to admit campaign #{campaign.id}',
                'summary': f'Campaign {campaign.title} reached high-impact priority threshold.',
                'priority': ApprovalPriority.HIGH,
                'status': ApprovalRequestStatus.PENDING,
                'requested_at': timezone.now(),
                'metadata': {'source': 'autonomy_scheduler', 'campaign_id': campaign.id, 'actor': actor},
            },
        )
    admission.status = CampaignAdmissionStatus.ADMITTED
    admission.admitted_at = timezone.now()
    admission.blocked_reasons = []
    admission.metadata = {**(admission.metadata or {}), 'admitted_by': actor, 'requires_approval': requires_approval}
    admission.save(update_fields=['status', 'admitted_at', 'blocked_reasons', 'metadata', 'updated_at'])
    return admission


@transaction.atomic
def defer_campaign(*, campaign_id: int, actor: str = 'operator-ui', deferred_until=None, reason: str = '') -> CampaignAdmission:
    admission = CampaignAdmission.objects.get(campaign_id=campaign_id)
    admission.status = CampaignAdmissionStatus.DEFERRED
    admission.deferred_until = deferred_until
    reasons = list(admission.blocked_reasons or [])
    if reason:
        reasons.append(reason)
    admission.blocked_reasons = reasons
    admission.metadata = {**(admission.metadata or {}), 'deferred_by': actor, 'deferred_reason': reason}
    admission.save(update_fields=['status', 'deferred_until', 'blocked_reasons', 'metadata', 'updated_at'])
    return admission

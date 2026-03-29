from __future__ import annotations

from django.utils import timezone

from apps.autonomy_campaign.models import AutonomyCampaignStatus
from apps.autonomy_campaign.services.execution import abort_campaign
from apps.autonomy_disposition.models import CampaignDisposition, CampaignDispositionStatus


def apply_campaign_disposition(*, disposition: CampaignDisposition, actor: str) -> CampaignDisposition:
    campaign = disposition.campaign
    state_before = campaign.status

    if disposition.disposition_status in {CampaignDispositionStatus.APPLIED, CampaignDispositionStatus.REJECTED, CampaignDispositionStatus.EXPIRED}:
        return disposition

    if disposition.requires_approval:
        if not disposition.linked_approval_request_id:
            disposition.disposition_status = CampaignDispositionStatus.APPROVAL_REQUIRED
            disposition.save(update_fields=['disposition_status', 'updated_at'])
            return disposition
        if disposition.linked_approval_request.status != 'APPROVED':
            disposition.disposition_status = CampaignDispositionStatus.BLOCKED
            disposition.save(update_fields=['disposition_status', 'updated_at'])
            return disposition

    if disposition.disposition_type == 'ABORTED':
        abort_campaign(campaign=campaign, reason=disposition.rationale, actor=actor)
    elif disposition.disposition_type in {'CLOSED', 'COMPLETED_RECORDED'}:
        campaign.status = AutonomyCampaignStatus.COMPLETED
        campaign.save(update_fields=['status', 'updated_at'])
    elif disposition.disposition_type == 'RETIRED':
        campaign.metadata = {**(campaign.metadata or {}), 'retired': True, 'retired_by': actor, 'retired_at': timezone.now().isoformat()}
        if campaign.status == AutonomyCampaignStatus.RUNNING:
            campaign.status = AutonomyCampaignStatus.PAUSED
            campaign.save(update_fields=['status', 'metadata', 'updated_at'])
        else:
            campaign.save(update_fields=['metadata', 'updated_at'])

    disposition.campaign_state_before = state_before
    disposition.campaign_state_after = campaign.status
    disposition.applied_by = actor
    disposition.applied_at = timezone.now()
    disposition.disposition_status = CampaignDispositionStatus.APPLIED
    disposition.save(
        update_fields=['campaign_state_before', 'campaign_state_after', 'applied_by', 'applied_at', 'disposition_status', 'updated_at']
    )
    return disposition

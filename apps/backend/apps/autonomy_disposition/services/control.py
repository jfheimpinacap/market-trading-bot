from __future__ import annotations

from django.utils import timezone

from apps.approval_center.models import ApprovalRequest
from apps.autonomy_disposition.models import CampaignDisposition
from apps.autonomy_disposition.services.apply import apply_campaign_disposition


def request_disposition_approval(*, disposition: CampaignDisposition, actor: str) -> ApprovalRequest:
    source_object_id = f'autonomy_disposition:{disposition.id}:campaign:{disposition.campaign_id}'
    existing = ApprovalRequest.objects.filter(source_type='other', source_object_id=source_object_id, status='PENDING').first()
    if existing:
        disposition.linked_approval_request = existing
        disposition.disposition_status = 'APPROVAL_REQUIRED'
        disposition.save(update_fields=['linked_approval_request', 'disposition_status', 'updated_at'])
        return existing

    request = ApprovalRequest.objects.create(
        source_type='other',
        source_object_id=source_object_id,
        title=f'Autonomy disposition approval for campaign #{disposition.campaign_id}',
        summary=disposition.rationale,
        priority='HIGH' if disposition.disposition_type in {'ABORTED', 'RETIRED'} else 'MEDIUM',
        status='PENDING',
        requested_at=timezone.now(),
        metadata={
            'autonomy_campaign_id': disposition.campaign_id,
            'autonomy_disposition_id': disposition.id,
            'requested_by': actor,
            'disposition_type': disposition.disposition_type,
        },
    )
    disposition.linked_approval_request = request
    disposition.disposition_status = 'APPROVAL_REQUIRED'
    disposition.save(update_fields=['linked_approval_request', 'disposition_status', 'updated_at'])
    return request


def apply_disposition(*, disposition: CampaignDisposition, actor: str) -> CampaignDisposition:
    return apply_campaign_disposition(disposition=disposition, actor=actor)

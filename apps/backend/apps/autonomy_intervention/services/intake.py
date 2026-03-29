from __future__ import annotations

from apps.autonomy_intervention.models import (
    CampaignInterventionRequest,
    InterventionRequestStatus,
    InterventionSourceType,
)


def create_intervention_request(*, campaign, requested_action: str, source_type: str = InterventionSourceType.MANUAL, severity: str = 'MEDIUM', rationale: str = '', reason_codes=None, blockers=None, linked_signal=None, linked_recommendation=None, requested_by: str = 'operator-ui', metadata=None, approval_required: bool = False):
    status = InterventionRequestStatus.APPROVAL_REQUIRED if approval_required else InterventionRequestStatus.OPEN
    return CampaignInterventionRequest.objects.create(
        campaign=campaign,
        source_type=source_type,
        requested_action=requested_action,
        request_status=status,
        severity=severity or 'MEDIUM',
        rationale=rationale or f'Manual intervention request for {requested_action}.',
        reason_codes=reason_codes or [],
        blockers=blockers or [],
        linked_signal=linked_signal,
        linked_recommendation=linked_recommendation,
        requested_by=requested_by,
        metadata=metadata or {},
    )

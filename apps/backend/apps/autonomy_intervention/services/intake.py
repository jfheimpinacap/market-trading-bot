from __future__ import annotations

<<<<<<< HEAD
from apps.autonomy_intervention.models import CampaignInterventionRequest
from apps.autonomy_intervention.services.validation import validate_request
from apps.autonomy_operations.models import CampaignAttentionSignal, CampaignRuntimeSnapshot, OperationsRecommendation


def create_request(
    *,
    campaign,
    source_type: str,
    requested_action: str,
    severity: str,
    rationale: str,
    reason_codes: list[str] | None = None,
    blockers: list[str] | None = None,
    linked_signal_id: int | None = None,
    linked_recommendation_id: int | None = None,
    requested_by: str = 'operator-ui',
    metadata: dict | None = None,
):
    linked_signal = CampaignAttentionSignal.objects.filter(pk=linked_signal_id).first() if linked_signal_id else None
    linked_recommendation = OperationsRecommendation.objects.filter(pk=linked_recommendation_id).first() if linked_recommendation_id else None
    runtime_snapshot = CampaignRuntimeSnapshot.objects.filter(campaign=campaign).order_by('-created_at', '-id').first()

    inferred_reason_codes = list(reason_codes or [])
    if linked_signal:
        inferred_reason_codes.extend([code for code in linked_signal.reason_codes if code not in inferred_reason_codes])
    if linked_recommendation:
        inferred_reason_codes.extend([code for code in linked_recommendation.reason_codes if code not in inferred_reason_codes])

    request_status, inferred_blockers = validate_request(campaign=campaign, requested_action=requested_action, runtime_snapshot=runtime_snapshot)
    final_blockers = list(blockers or []) + [item for item in inferred_blockers if item not in (blockers or [])]

=======
from apps.autonomy_intervention.models import (
    CampaignInterventionRequest,
    InterventionRequestStatus,
    InterventionSourceType,
)


def create_intervention_request(*, campaign, requested_action: str, source_type: str = InterventionSourceType.MANUAL, severity: str = 'MEDIUM', rationale: str = '', reason_codes=None, blockers=None, linked_signal=None, linked_recommendation=None, requested_by: str = 'operator-ui', metadata=None, approval_required: bool = False):
    status = InterventionRequestStatus.APPROVAL_REQUIRED if approval_required else InterventionRequestStatus.OPEN
>>>>>>> origin/main
    return CampaignInterventionRequest.objects.create(
        campaign=campaign,
        source_type=source_type,
        requested_action=requested_action,
<<<<<<< HEAD
        request_status=request_status,
        severity=(severity or 'MEDIUM').upper(),
        rationale=rationale,
        reason_codes=inferred_reason_codes,
        blockers=final_blockers,
=======
        request_status=status,
        severity=severity or 'MEDIUM',
        rationale=rationale or f'Manual intervention request for {requested_action}.',
        reason_codes=reason_codes or [],
        blockers=blockers or [],
>>>>>>> origin/main
        linked_signal=linked_signal,
        linked_recommendation=linked_recommendation,
        requested_by=requested_by,
        metadata=metadata or {},
    )

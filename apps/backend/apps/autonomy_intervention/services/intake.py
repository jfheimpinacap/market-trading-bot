from __future__ import annotations

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

    return CampaignInterventionRequest.objects.create(
        campaign=campaign,
        source_type=source_type,
        requested_action=requested_action,
        request_status=request_status,
        severity=(severity or 'MEDIUM').upper(),
        rationale=rationale,
        reason_codes=inferred_reason_codes,
        blockers=final_blockers,
        linked_signal=linked_signal,
        linked_recommendation=linked_recommendation,
        requested_by=requested_by,
        metadata=metadata or {},
    )

from __future__ import annotations

from django.utils import timezone

from apps.certification_board.models import (
    BaselineResponseCase,
    DownstreamAcknowledgement,
    DownstreamAcknowledgementStatus,
    ResponseCaseDownstreamStatus,
    ResponseRoutingAction,
)
from apps.certification_board.services.baseline_response_actions.tracking import create_tracking_record

ACK_TO_TRACKING_STATUS = {
    DownstreamAcknowledgementStatus.SENT: ResponseCaseDownstreamStatus.SENT,
    DownstreamAcknowledgementStatus.ACKNOWLEDGED: ResponseCaseDownstreamStatus.ACKNOWLEDGED,
    DownstreamAcknowledgementStatus.ACCEPTED_FOR_REVIEW: ResponseCaseDownstreamStatus.UNDER_REVIEW,
    DownstreamAcknowledgementStatus.WAITING_MORE_EVIDENCE: ResponseCaseDownstreamStatus.WAITING_EVIDENCE,
    DownstreamAcknowledgementStatus.REJECTED_BY_TARGET: ResponseCaseDownstreamStatus.REJECTED,
}


def create_or_update_acknowledgement(
    *,
    response_case: BaselineResponseCase,
    routing_action: ResponseRoutingAction | None = None,
    acknowledgement_status: str = DownstreamAcknowledgementStatus.SENT,
    acknowledged_by: str = '',
    acknowledgement_notes: str = '',
    linked_target_reference: str = '',
    metadata: dict | None = None,
) -> DownstreamAcknowledgement:
    reference_action = routing_action or response_case.routing_actions.order_by('-created_at', '-id').first()
    acknowledgement, _ = DownstreamAcknowledgement.objects.update_or_create(
        linked_response_case=response_case,
        linked_response_routing_action=reference_action,
        defaults={
            'routing_target': (reference_action.routing_target if reference_action else ''),
            'acknowledgement_status': acknowledgement_status,
            'acknowledged_by': acknowledged_by,
            'acknowledged_at': timezone.now()
            if acknowledgement_status not in {DownstreamAcknowledgementStatus.SENT, DownstreamAcknowledgementStatus.NO_RESPONSE}
            else None,
            'acknowledgement_notes': acknowledgement_notes,
            'linked_target_reference': linked_target_reference,
            'metadata': metadata or {},
        },
    )
    tracking_status = ACK_TO_TRACKING_STATUS.get(acknowledgement_status)
    if tracking_status:
        create_tracking_record(
            response_case=response_case,
            routing_action=reference_action,
            downstream_status=tracking_status,
            tracking_notes=acknowledgement_notes,
            tracked_by=acknowledged_by,
            linked_downstream_reference=linked_target_reference,
            metadata={'source': 'baseline-response-lifecycle', **(metadata or {})},
        )
    return acknowledgement

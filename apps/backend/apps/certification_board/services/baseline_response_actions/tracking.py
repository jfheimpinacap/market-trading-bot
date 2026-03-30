from __future__ import annotations

from django.utils import timezone

from apps.certification_board.models import (
    BaselineResponseCase,
    BaselineResponseCaseStatus,
    ResponseCaseDownstreamStatus,
    ResponseCaseTrackingRecord,
    ResponseRoutingAction,
    ResponseRoutingActionStatus,
)


STATUS_TO_CASE_STATUS = {
    ResponseCaseDownstreamStatus.SENT: BaselineResponseCaseStatus.ROUTED,
    ResponseCaseDownstreamStatus.ACKNOWLEDGED: BaselineResponseCaseStatus.UNDER_REVIEW,
    ResponseCaseDownstreamStatus.UNDER_REVIEW: BaselineResponseCaseStatus.UNDER_REVIEW,
    ResponseCaseDownstreamStatus.WAITING_EVIDENCE: BaselineResponseCaseStatus.UNDER_REVIEW,
    ResponseCaseDownstreamStatus.COMPLETED: BaselineResponseCaseStatus.ROUTED,
    ResponseCaseDownstreamStatus.CLOSED_NO_ACTION: BaselineResponseCaseStatus.CLOSED_NO_ACTION,
    ResponseCaseDownstreamStatus.ESCALATED: BaselineResponseCaseStatus.ESCALATED,
    ResponseCaseDownstreamStatus.REJECTED: BaselineResponseCaseStatus.DEFERRED,
}


def create_tracking_record(
    *,
    response_case: BaselineResponseCase,
    routing_action: ResponseRoutingAction | None,
    downstream_status: str,
    tracking_notes: str = '',
    tracked_by: str = '',
    linked_downstream_reference: str = '',
    metadata: dict | None = None,
) -> ResponseCaseTrackingRecord:
    record = ResponseCaseTrackingRecord.objects.create(
        linked_response_case=response_case,
        linked_routing_action=routing_action,
        downstream_status=downstream_status,
        tracking_notes=tracking_notes,
        tracked_by=tracked_by,
        tracked_at=timezone.now(),
        linked_downstream_reference=linked_downstream_reference,
        metadata=metadata or {},
    )
    response_case.case_status = STATUS_TO_CASE_STATUS.get(downstream_status, response_case.case_status)
    response_case.save(update_fields=['case_status', 'updated_at'])
    return record


def close_response_case_no_action(
    *,
    response_case: BaselineResponseCase,
    routing_action: ResponseRoutingAction | None,
    tracked_by: str,
    tracking_notes: str = 'Case closed manually with no downstream action.',
    linked_downstream_reference: str = '',
    metadata: dict | None = None,
) -> ResponseCaseTrackingRecord:
    if routing_action is not None:
        routing_action.action_status = ResponseRoutingActionStatus.CLOSED
        routing_action.metadata = {**(routing_action.metadata or {}), 'closed_no_action': True, **(metadata or {})}
        routing_action.save(update_fields=['action_status', 'metadata', 'updated_at'])

    return create_tracking_record(
        response_case=response_case,
        routing_action=routing_action,
        downstream_status=ResponseCaseDownstreamStatus.CLOSED_NO_ACTION,
        tracking_notes=tracking_notes,
        tracked_by=tracked_by,
        linked_downstream_reference=linked_downstream_reference,
        metadata=metadata or {},
    )

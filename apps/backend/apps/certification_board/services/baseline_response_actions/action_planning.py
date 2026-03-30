from __future__ import annotations

from apps.certification_board.models import (
    BaselineResponseType,
    ResponseActionResolutionStatus,
    ResponseActionCandidate,
    ResponseRoutingAction,
    ResponseRoutingActionStatus,
    ResponseRoutingActionType,
)


TARGET_TO_ACTION = {
    'evaluation_lab': ResponseRoutingActionType.SEND_TO_EVALUATION_REVIEW,
    'tuning_board': ResponseRoutingActionType.SEND_TO_TUNING_REVIEW,
    'certification_board': ResponseRoutingActionType.SEND_TO_CERTIFICATION_REVIEW,
    'promotion_committee': ResponseRoutingActionType.SEND_TO_PROMOTION_RECHECK,
    'rollback_review': ResponseRoutingActionType.SEND_TO_ROLLBACK_REVIEW,
    'monitoring_only': ResponseRoutingActionType.KEEP_IN_MONITORING,
}


def _resolve_action_type(candidate: ResponseActionCandidate) -> str:
    if candidate.routing_resolution_status in {ResponseActionResolutionStatus.BLOCKED, ResponseActionResolutionStatus.UNKNOWN}:
        return ResponseRoutingActionType.REQUIRE_ROUTING_RECHECK
    if candidate.linked_response_case.response_type == BaselineResponseType.KEEP_UNDER_WATCH:
        return ResponseRoutingActionType.KEEP_IN_MONITORING
    return TARGET_TO_ACTION.get(candidate.intended_routing_target, ResponseRoutingActionType.REQUIRE_ROUTING_RECHECK)


def _resolve_status(candidate: ResponseActionCandidate, action_type: str) -> str:
    if action_type == ResponseRoutingActionType.REQUIRE_ROUTING_RECHECK:
        return ResponseRoutingActionStatus.BLOCKED
    if action_type == ResponseRoutingActionType.KEEP_IN_MONITORING:
        return ResponseRoutingActionStatus.DEFERRED
    if candidate.ready_for_action:
        return ResponseRoutingActionStatus.READY_TO_ROUTE
    return ResponseRoutingActionStatus.PROPOSED


def plan_routing_actions(*, candidates: list[ResponseActionCandidate]) -> list[ResponseRoutingAction]:
    actions: list[ResponseRoutingAction] = []
    for candidate in candidates:
        action_type = _resolve_action_type(candidate)
        existing = ResponseRoutingAction.objects.filter(
            linked_response_case=candidate.linked_response_case,
            action_type=action_type,
            action_status__in=[
                ResponseRoutingActionStatus.PROPOSED,
                ResponseRoutingActionStatus.READY_TO_ROUTE,
                ResponseRoutingActionStatus.ROUTED,
                ResponseRoutingActionStatus.BLOCKED,
                ResponseRoutingActionStatus.DEFERRED,
            ],
        ).order_by('-created_at', '-id').first()
        if existing:
            actions.append(existing)
            continue

        action = ResponseRoutingAction.objects.create(
            linked_candidate=candidate,
            linked_response_case=candidate.linked_response_case,
            action_type=action_type,
            action_status=_resolve_status(candidate, action_type),
            routing_target=candidate.intended_routing_target,
            rationale=(candidate.linked_routing_decision.routing_rationale if candidate.linked_routing_decision else 'Manual routing recheck required.'),
            reason_codes=['manual_first_handoff'],
            blockers=candidate.blockers,
            metadata={'routing_resolution_status': candidate.routing_resolution_status},
        )
        actions.append(action)
    return actions

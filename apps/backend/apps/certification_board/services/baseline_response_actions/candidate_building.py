from __future__ import annotations

from apps.certification_board.models import (
    BaselineResponseCase,
    BaselineResponseCaseStatus,
    ResponseActionCandidate,
    ResponseActionResolutionStatus,
    ResponseRoutingDecision,
)


def _resolution_status(decision: ResponseRoutingDecision | None) -> str:
    if decision is None or not decision.routing_target:
        return ResponseActionResolutionStatus.UNKNOWN
    if decision.routing_status == 'BLOCKED':
        return ResponseActionResolutionStatus.BLOCKED
    if decision.routing_status in {'READY', 'SENT'}:
        return ResponseActionResolutionStatus.RESOLVED
    if decision.routing_status in {'PROPOSED', 'DEFERRED'}:
        return ResponseActionResolutionStatus.PARTIAL
    return ResponseActionResolutionStatus.UNKNOWN


def build_action_candidates(*, action_run) -> list[ResponseActionCandidate]:
    cases = BaselineResponseCase.objects.filter(
        case_status__in=[BaselineResponseCaseStatus.OPEN, BaselineResponseCaseStatus.UNDER_REVIEW]
    ).select_related('routing_decision')

    candidates: list[ResponseActionCandidate] = []
    for response_case in cases:
        decision = getattr(response_case, 'routing_decision', None)
        resolution = _resolution_status(decision)
        blockers = list(response_case.blockers or [])
        if resolution in {ResponseActionResolutionStatus.BLOCKED, ResponseActionResolutionStatus.UNKNOWN}:
            blockers.append('routing_resolution_incomplete')

        candidate = ResponseActionCandidate.objects.create(
            action_run=action_run,
            linked_response_case=response_case,
            linked_routing_decision=decision,
            target_component=response_case.target_component,
            target_scope=response_case.target_scope,
            intended_routing_target=(decision.routing_target if decision else ''),
            routing_resolution_status=resolution,
            ready_for_action=resolution == ResponseActionResolutionStatus.RESOLVED,
            blockers=sorted(set(blockers)),
            metadata={'response_type': response_case.response_type, 'priority_level': response_case.priority_level},
        )
        candidates.append(candidate)
    return candidates

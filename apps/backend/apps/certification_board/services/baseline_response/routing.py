from __future__ import annotations

from apps.certification_board.models import (
    BaselineResponseCase,
    BaselineResponseRoutingStatus,
    BaselineResponseRoutingTarget,
    BaselineResponseType,
    ResponseRoutingDecision,
)


def build_routing_decision(*, response_case: BaselineResponseCase) -> ResponseRoutingDecision:
    if response_case.response_type == BaselineResponseType.KEEP_UNDER_WATCH:
        routing_target = BaselineResponseRoutingTarget.MONITORING_ONLY
    elif response_case.response_type == BaselineResponseType.OPEN_REEVALUATION:
        routing_target = BaselineResponseRoutingTarget.EVALUATION_LAB
    elif response_case.response_type == BaselineResponseType.OPEN_TUNING_REVIEW:
        routing_target = BaselineResponseRoutingTarget.TUNING_BOARD
    elif response_case.response_type == BaselineResponseType.PREPARE_ROLLBACK_REVIEW:
        routing_target = BaselineResponseRoutingTarget.ROLLBACK_REVIEW
    elif response_case.response_type == BaselineResponseType.REQUIRE_MANUAL_BASELINE_REVIEW:
        routing_target = BaselineResponseRoutingTarget.CERTIFICATION_BOARD
    else:
        routing_target = BaselineResponseRoutingTarget.PROMOTION_COMMITTEE

    routing_status = BaselineResponseRoutingStatus.READY if not response_case.blockers else BaselineResponseRoutingStatus.BLOCKED

    return ResponseRoutingDecision.objects.create(
        linked_response_case=response_case,
        routing_target=routing_target,
        routing_status=routing_status,
        routing_rationale=f"Route {response_case.response_type} to {routing_target} in manual-first mode.",
        metadata={
            'manual_only': True,
            'auto_apply': False,
            'blocker_count': len(response_case.blockers or []),
        },
    )

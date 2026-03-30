from __future__ import annotations

from decimal import Decimal

from django.utils import timezone

from apps.certification_board.models import (
    ResponseActionRecommendation,
    ResponseActionRecommendationType,
    ResponseCaseTrackingRecord,
    ResponseRoutingAction,
    ResponseRoutingActionStatus,
    ResponseRoutingActionType,
)


def build_action_recommendation(*, action_run, action: ResponseRoutingAction) -> ResponseActionRecommendation:
    recommendation_type = ResponseActionRecommendationType.ROUTE_CASE_NOW
    rationale = 'Routing target resolved and ready for explicit manual handoff.'
    reason_codes = ['ready_to_route']
    confidence = Decimal('0.7600')

    if action.action_type == ResponseRoutingActionType.REQUIRE_ROUTING_RECHECK:
        recommendation_type = ResponseActionRecommendationType.REQUIRE_ROUTING_RECHECK
        rationale = 'Routing target is ambiguous or blocked; operator recheck required.'
        reason_codes = ['routing_incomplete']
        confidence = Decimal('0.9300')
    elif action.action_type == ResponseRoutingActionType.KEEP_IN_MONITORING:
        recommendation_type = ResponseActionRecommendationType.KEEP_CASE_IN_MONITORING
        rationale = 'Case remains under manual monitoring with no downstream routing yet.'
        reason_codes = ['monitoring_only']
        confidence = Decimal('0.8200')
    elif action.linked_response_case.priority_level == 'CRITICAL':
        recommendation_type = ResponseActionRecommendationType.ESCALATE_CASE_PRIORITY
        rationale = 'Critical pressure detected; prioritize handoff and downstream acknowledgement.'
        reason_codes = ['critical_priority']
        confidence = Decimal('0.8800')

    last_tracking = ResponseCaseTrackingRecord.objects.filter(
        linked_response_case=action.linked_response_case,
    ).order_by('-tracked_at', '-id').first()
    if action.action_status == ResponseRoutingActionStatus.ROUTED and (
        last_tracking is None or (last_tracking.tracked_at and (timezone.now() - last_tracking.tracked_at).days >= 1)
    ):
        recommendation_type = ResponseActionRecommendationType.REQUIRE_DOWNSTREAM_STATUS_UPDATE
        rationale = 'Case was routed but has no recent downstream status update.'
        reason_codes = ['downstream_update_missing']
        confidence = Decimal('0.8700')

    return ResponseActionRecommendation.objects.create(
        action_run=action_run,
        target_action=action,
        recommendation_type=recommendation_type,
        rationale=rationale,
        reason_codes=reason_codes,
        confidence=confidence,
        blockers=action.blockers,
        metadata={'action_status': action.action_status},
    )

from __future__ import annotations

from apps.mission_control.models import (
    AutonomousHeartbeatDecision,
    AutonomousHeartbeatDecisionType,
    AutonomousHeartbeatRecommendation,
    AutonomousHeartbeatRecommendationType,
)


def emit_heartbeat_recommendation(*, decision: AutonomousHeartbeatDecision) -> AutonomousHeartbeatRecommendation:
    recommendation_type = AutonomousHeartbeatRecommendationType.WAIT_UNTIL_NEXT_DUE_WINDOW
    blockers: list[str] = []

    if decision.decision_type == AutonomousHeartbeatDecisionType.RUN_DUE_TICK:
        recommendation_type = AutonomousHeartbeatRecommendationType.RUN_DUE_TICK_NOW
    elif decision.decision_type == AutonomousHeartbeatDecisionType.SKIP_FOR_COOLDOWN:
        recommendation_type = AutonomousHeartbeatRecommendationType.SKIP_FOR_ACTIVE_COOLDOWN
    elif decision.decision_type == AutonomousHeartbeatDecisionType.PAUSE_SESSION:
        recommendation_type = AutonomousHeartbeatRecommendationType.PAUSE_FOR_RUNTIME_OR_SAFETY
        blockers = list(decision.reason_codes or [])
    elif decision.decision_type == AutonomousHeartbeatDecisionType.STOP_SESSION:
        recommendation_type = AutonomousHeartbeatRecommendationType.STOP_FOR_KILL_SWITCH
        blockers = list(decision.reason_codes or [])
    elif decision.decision_type == AutonomousHeartbeatDecisionType.BLOCK_SESSION:
        recommendation_type = AutonomousHeartbeatRecommendationType.REQUIRE_MANUAL_RUNNER_REVIEW
        blockers = list(decision.reason_codes or [])

    return AutonomousHeartbeatRecommendation.objects.create(
        recommendation_type=recommendation_type,
        target_session=decision.linked_session,
        target_heartbeat_decision=decision,
        rationale=f'{decision.decision_summary} Recommendation={recommendation_type}.',
        reason_codes=list(decision.reason_codes or []),
        confidence=0.8 if not blockers else 0.95,
        blockers=blockers,
    )

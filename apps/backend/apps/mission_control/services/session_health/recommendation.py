from __future__ import annotations

from apps.mission_control.models import (
    AutonomousSessionHealthRecommendation,
    AutonomousSessionHealthRecommendationType,
    AutonomousSessionInterventionDecision,
    AutonomousSessionInterventionDecisionType,
)


def emit_health_recommendation(*, decision: AutonomousSessionInterventionDecision) -> AutonomousSessionHealthRecommendation:
    recommendation_type = AutonomousSessionHealthRecommendationType.KEEP_SESSION_RUNNING
    blockers: list[str] = []
    confidence = 0.7

    if decision.decision_type == AutonomousSessionInterventionDecisionType.PAUSE_SESSION:
        recommendation_type = AutonomousSessionHealthRecommendationType.PAUSE_FOR_STABILIZATION
        confidence = 0.82
    elif decision.decision_type == AutonomousSessionInterventionDecisionType.STOP_SESSION:
        recommendation_type = AutonomousSessionHealthRecommendationType.STOP_FOR_PERSISTENT_BLOCKS
        confidence = 0.9
    elif decision.decision_type == AutonomousSessionInterventionDecisionType.RESUME_SESSION:
        recommendation_type = AutonomousSessionHealthRecommendationType.RESUME_AFTER_RECOVERY
        confidence = 0.75
    elif decision.decision_type == AutonomousSessionInterventionDecisionType.REQUIRE_MANUAL_REVIEW:
        recommendation_type = AutonomousSessionHealthRecommendationType.REQUIRE_MANUAL_HEALTH_REVIEW
        blockers = ['manual_health_confirmation_required']
        confidence = 0.6
    elif decision.decision_type == AutonomousSessionInterventionDecisionType.ESCALATE_TO_INCIDENT_REVIEW:
        recommendation_type = AutonomousSessionHealthRecommendationType.ESCALATE_TO_INCIDENT_LAYER
        blockers = ['incident_commander_review_pending']
        confidence = 0.88

    return AutonomousSessionHealthRecommendation.objects.create(
        recommendation_type=recommendation_type,
        target_session=decision.linked_session,
        target_health_snapshot=decision.linked_health_snapshot,
        target_intervention_decision=decision,
        rationale=decision.decision_summary,
        reason_codes=decision.reason_codes,
        confidence=confidence,
        blockers=blockers,
    )

from __future__ import annotations

from apps.mission_control.models import (
    AutonomousResumeDecision,
    AutonomousResumeDecisionType,
    AutonomousSessionRecoveryRecommendation,
    AutonomousSessionRecoveryRecommendationType,
)


def emit_recovery_recommendation(*, decision: AutonomousResumeDecision) -> AutonomousSessionRecoveryRecommendation:
    recommendation_type = AutonomousSessionRecoveryRecommendationType.KEEP_SESSION_PAUSED
    confidence = 0.5

    if decision.decision_type == AutonomousResumeDecisionType.READY_TO_RESUME:
        recommendation_type = AutonomousSessionRecoveryRecommendationType.RESUME_SESSION_SAFELY
        confidence = 0.85
    elif decision.decision_type == AutonomousResumeDecisionType.RESUME_IN_MONITOR_ONLY_MODE:
        recommendation_type = AutonomousSessionRecoveryRecommendationType.RESUME_IN_MONITOR_ONLY_MODE
        confidence = 0.7
    elif decision.decision_type == AutonomousResumeDecisionType.REQUIRE_MANUAL_RECOVERY_REVIEW:
        recommendation_type = AutonomousSessionRecoveryRecommendationType.REQUIRE_MANUAL_RECOVERY_REVIEW
        confidence = 0.75
    elif decision.decision_type == AutonomousResumeDecisionType.STOP_SESSION_PERMANENTLY:
        recommendation_type = AutonomousSessionRecoveryRecommendationType.STOP_SESSION_FOR_UNRECOVERABLE_STATE
        confidence = 0.95
    elif decision.decision_type == AutonomousResumeDecisionType.ESCALATE_TO_INCIDENT_REVIEW:
        recommendation_type = AutonomousSessionRecoveryRecommendationType.ESCALATE_RECOVERY_TO_INCIDENT_LAYER
        confidence = 0.9

    rationale = f'recommendation={recommendation_type} from decision={decision.decision_type} for session={decision.linked_session_id}'
    return AutonomousSessionRecoveryRecommendation.objects.create(
        recommendation_type=recommendation_type,
        target_session=decision.linked_session,
        target_recovery_snapshot=decision.linked_recovery_snapshot,
        target_resume_decision=decision,
        rationale=rationale,
        reason_codes=decision.reason_codes,
        confidence=confidence,
        blockers=decision.metadata.get('blocker_types', []),
    )

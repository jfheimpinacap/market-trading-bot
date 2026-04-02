from __future__ import annotations

from apps.mission_control.models import (
    AutonomousSessionAdmissionDecision,
    AutonomousSessionAdmissionDecisionType,
    AutonomousSessionAdmissionRecommendation,
    AutonomousSessionAdmissionRecommendationType,
)


def emit_admission_recommendation(*, decision: AutonomousSessionAdmissionDecision) -> AutonomousSessionAdmissionRecommendation:
    mapping = {
        AutonomousSessionAdmissionDecisionType.ADMIT_SESSION: AutonomousSessionAdmissionRecommendationType.ADMIT_HIGH_PRIORITY_SESSION,
        AutonomousSessionAdmissionDecisionType.ALLOW_RESUME: AutonomousSessionAdmissionRecommendationType.ALLOW_SAFE_RESUME,
        AutonomousSessionAdmissionDecisionType.PARK_SESSION: AutonomousSessionAdmissionRecommendationType.PARK_LOW_SIGNAL_SESSION,
        AutonomousSessionAdmissionDecisionType.DEFER_SESSION: AutonomousSessionAdmissionRecommendationType.DEFER_FOR_CAPACITY_PRESSURE,
        AutonomousSessionAdmissionDecisionType.PAUSE_SESSION: AutonomousSessionAdmissionRecommendationType.PAUSE_FOR_GLOBAL_THROTTLE,
        AutonomousSessionAdmissionDecisionType.RETIRE_SESSION: AutonomousSessionAdmissionRecommendationType.RETIRE_LOW_VALUE_SESSION,
        AutonomousSessionAdmissionDecisionType.REQUIRE_MANUAL_ADMISSION_REVIEW: AutonomousSessionAdmissionRecommendationType.REQUIRE_MANUAL_ADMISSION_REVIEW,
    }
    recommendation_type = mapping[decision.decision_type]
    blockers = []
    if decision.decision_type in {
        AutonomousSessionAdmissionDecisionType.DEFER_SESSION,
        AutonomousSessionAdmissionDecisionType.PAUSE_SESSION,
        AutonomousSessionAdmissionDecisionType.REQUIRE_MANUAL_ADMISSION_REVIEW,
    }:
        blockers = decision.reason_codes
    return AutonomousSessionAdmissionRecommendation.objects.create(
        recommendation_type=recommendation_type,
        target_session=decision.linked_session,
        target_admission_review=decision.linked_admission_review,
        target_admission_decision=decision,
        rationale=decision.decision_summary,
        reason_codes=decision.reason_codes,
        confidence=0.72 if decision.auto_applicable else 0.55,
        blockers=blockers,
    )

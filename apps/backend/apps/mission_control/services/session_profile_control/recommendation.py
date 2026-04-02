from __future__ import annotations

from apps.mission_control.models import (
    AutonomousProfileRecommendation,
    AutonomousProfileRecommendationType,
    AutonomousProfileSwitchDecision,
    AutonomousProfileSwitchDecisionType,
)


_DECISION_TO_RECOMMENDATION = {
    AutonomousProfileSwitchDecisionType.KEEP_CURRENT_PROFILE: AutonomousProfileRecommendationType.KEEP_BALANCED_PROFILE,
    AutonomousProfileSwitchDecisionType.SWITCH_TO_CONSERVATIVE_QUIET: AutonomousProfileRecommendationType.SHIFT_TO_CONSERVATIVE_QUIET_PROFILE,
    AutonomousProfileSwitchDecisionType.SWITCH_TO_MONITOR_HEAVY: AutonomousProfileRecommendationType.SHIFT_TO_MONITOR_HEAVY_PROFILE,
    AutonomousProfileSwitchDecisionType.SWITCH_TO_BALANCED_LOCAL: AutonomousProfileRecommendationType.RESTORE_BALANCED_PROFILE,
    AutonomousProfileSwitchDecisionType.REQUIRE_MANUAL_PROFILE_REVIEW: AutonomousProfileRecommendationType.REQUIRE_MANUAL_PROFILE_REVIEW,
    AutonomousProfileSwitchDecisionType.BLOCK_PROFILE_SWITCH: AutonomousProfileRecommendationType.BLOCK_AUTOMATIC_PROFILE_SWITCH,
}


def emit_profile_recommendation(*, decision: AutonomousProfileSwitchDecision) -> AutonomousProfileRecommendation:
    recommendation_type = _DECISION_TO_RECOMMENDATION[decision.decision_type]
    blockers: list[str] = []
    confidence = 0.75
    if decision.decision_type in {
        AutonomousProfileSwitchDecisionType.BLOCK_PROFILE_SWITCH,
        AutonomousProfileSwitchDecisionType.REQUIRE_MANUAL_PROFILE_REVIEW,
    }:
        blockers = ['runtime_or_safety_conflict']
        confidence = 0.55

    return AutonomousProfileRecommendation.objects.create(
        recommendation_type=recommendation_type,
        target_session=decision.linked_session,
        target_context_review=decision.linked_context_review,
        target_switch_decision=decision,
        rationale=decision.decision_summary,
        reason_codes=decision.reason_codes,
        confidence=confidence,
        blockers=blockers,
    )

from __future__ import annotations

from apps.runtime_governor.models import (
    GlobalOperatingMode,
    GlobalOperatingModeDecision,
    GlobalOperatingModeDecisionType,
    GlobalOperatingModeRecommendation,
    GlobalOperatingModeRecommendationType,
)


def emit_mode_recommendation(*, decision: GlobalOperatingModeDecision) -> GlobalOperatingModeRecommendation:
    mapping = {
        GlobalOperatingModeDecisionType.KEEP_CURRENT_MODE: GlobalOperatingModeRecommendationType.KEEP_BALANCED_MODE,
        GlobalOperatingModeDecisionType.SWITCH_TO_CAUTION: GlobalOperatingModeRecommendationType.SHIFT_TO_CAUTION_MODE,
        GlobalOperatingModeDecisionType.SWITCH_TO_MONITOR_ONLY: GlobalOperatingModeRecommendationType.SHIFT_TO_MONITOR_ONLY_MODE,
        GlobalOperatingModeDecisionType.SWITCH_TO_RECOVERY_MODE: GlobalOperatingModeRecommendationType.ENTER_RECOVERY_MODE,
        GlobalOperatingModeDecisionType.SWITCH_TO_THROTTLED: GlobalOperatingModeRecommendationType.THROTTLE_GLOBAL_ACTIVITY,
        GlobalOperatingModeDecisionType.SWITCH_TO_BLOCKED: GlobalOperatingModeRecommendationType.BLOCK_NEW_ACTIVITY_GLOBALLY,
        GlobalOperatingModeDecisionType.REQUIRE_MANUAL_MODE_REVIEW: GlobalOperatingModeRecommendationType.REQUIRE_MANUAL_MODE_REVIEW,
    }

    recommendation_type = mapping.get(decision.decision_type, GlobalOperatingModeRecommendationType.REQUIRE_MANUAL_MODE_REVIEW)
    blockers: list[str] = []
    confidence = 0.7
    if recommendation_type == GlobalOperatingModeRecommendationType.REQUIRE_MANUAL_MODE_REVIEW:
        blockers.append('Ambiguous global signals; manual review required.')
        confidence = 0.4
    elif decision.target_mode in {GlobalOperatingMode.BLOCKED, GlobalOperatingMode.THROTTLED}:
        confidence = 0.9

    return GlobalOperatingModeRecommendation.objects.create(
        recommendation_type=recommendation_type,
        target_posture_snapshot=decision.linked_posture_snapshot,
        target_mode_decision=decision,
        rationale=decision.decision_summary,
        reason_codes=decision.reason_codes,
        confidence=confidence,
        blockers=blockers,
        metadata={'target_mode': decision.target_mode},
    )

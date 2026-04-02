from __future__ import annotations

from apps.runtime_governor.models import (
    GlobalModeEnforcementRecommendation,
    GlobalModeEnforcementRecommendationType,
    GlobalOperatingMode,
)


def emit_enforcement_recommendations(*, enforcement_run, impacts: list, decisions: list) -> list[GlobalModeEnforcementRecommendation]:
    mode = enforcement_run.current_mode
    if mode == GlobalOperatingMode.BALANCED:
        recommendation_type = GlobalModeEnforcementRecommendationType.KEEP_BALANCED_ENFORCEMENT
        confidence = 0.8
    elif mode == GlobalOperatingMode.CAUTION:
        recommendation_type = GlobalModeEnforcementRecommendationType.REDUCE_RUNTIME_INTENSITY
        confidence = 0.85
    elif mode == GlobalOperatingMode.MONITOR_ONLY:
        recommendation_type = GlobalModeEnforcementRecommendationType.ENTER_MONITOR_ONLY_BEHAVIOR
        confidence = 0.95
    elif mode == GlobalOperatingMode.RECOVERY_MODE:
        recommendation_type = GlobalModeEnforcementRecommendationType.BIAS_TOWARD_MANUAL_REVIEW
        confidence = 0.9
    elif mode == GlobalOperatingMode.THROTTLED:
        recommendation_type = GlobalModeEnforcementRecommendationType.THROTTLE_GLOBAL_NEW_ACTIVITY
        confidence = 0.92
    else:
        recommendation_type = GlobalModeEnforcementRecommendationType.BLOCK_NEW_EXECUTION_PATHS
        confidence = 0.99

    blocked_count = sum(1 for i in impacts if i.impact_status == 'BLOCKED')
    blockers = ['High restriction posture active.'] if blocked_count else []
    rationale = f'Mode enforcement propagated for {mode} with {blocked_count} blocked module(s).'

    recommendation = GlobalModeEnforcementRecommendation.objects.create(
        recommendation_type=recommendation_type,
        target_enforcement_run=enforcement_run,
        rationale=rationale,
        reason_codes=[f'mode:{mode}', f'blocked_modules:{blocked_count}'],
        confidence=confidence,
        blockers=blockers,
        metadata={'decision_count': len(decisions)},
    )
    return [recommendation]

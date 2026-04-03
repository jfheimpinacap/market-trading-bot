from __future__ import annotations

from apps.runtime_governor.models import (
    RuntimeModeStabilizationRecommendation,
    RuntimeModeStabilizationRecommendationType,
    RuntimeModeTransitionDecision,
    RuntimeModeTransitionDecisionType,
)


def emit_runtime_mode_stabilization_recommendation(
    *,
    transition_decision: RuntimeModeTransitionDecision,
) -> RuntimeModeStabilizationRecommendation:
    reason_codes = list(transition_decision.reason_codes or [])
    blockers: list[str] = []
    confidence = 0.65

    recommendation_type = RuntimeModeStabilizationRecommendationType.ALLOW_TRANSITION_NOW
    rationale = 'Stability review indicates transition can proceed now.'

    if transition_decision.decision_type == RuntimeModeTransitionDecisionType.KEEP_CURRENT_MODE_FOR_DWELL:
        recommendation_type = RuntimeModeStabilizationRecommendationType.HOLD_CURRENT_MODE_LONGER
        rationale = 'Current mode dwell is too short; hold mode longer before switching.'
        confidence = 0.78
        blockers.append('minimum_dwell_not_met')
    elif transition_decision.decision_type == RuntimeModeTransitionDecisionType.DEFER_MODE_SWITCH:
        if transition_decision.linked_transition_snapshot.current_mode == 'RECOVERY_MODE':
            recommendation_type = RuntimeModeStabilizationRecommendationType.KEEP_RECOVERY_MODE_UNTIL_STABLE
            rationale = 'Recovery mode should remain active until stable dwell and lower pressure are observed.'
        else:
            recommendation_type = RuntimeModeStabilizationRecommendationType.DEFER_RELAXATION
            rationale = 'Requested relaxation is deferred to avoid premature mode softening.'
        confidence = 0.82
        blockers.append('premature_relaxation')
    elif transition_decision.decision_type == RuntimeModeTransitionDecisionType.BLOCK_MODE_SWITCH:
        recommendation_type = RuntimeModeStabilizationRecommendationType.BLOCK_FLAPPING_TRANSITION
        rationale = 'Transition blocked due to flapping risk and unstable recent switching pattern.'
        confidence = 0.9
        blockers.append('flapping_risk')
    elif transition_decision.decision_type == RuntimeModeTransitionDecisionType.REQUIRE_MANUAL_STABILITY_REVIEW:
        recommendation_type = RuntimeModeStabilizationRecommendationType.REQUIRE_MANUAL_STABILITY_REVIEW
        rationale = 'Manual review is required because automatic stabilization confidence is insufficient.'
        confidence = 0.6
        blockers.append('manual_review_required')

    return RuntimeModeStabilizationRecommendation.objects.create(
        target_transition_snapshot=transition_decision.linked_transition_snapshot,
        target_stability_review=transition_decision.linked_stability_review,
        target_transition_decision=transition_decision,
        recommendation_type=recommendation_type,
        rationale=rationale,
        reason_codes=list(dict.fromkeys(reason_codes)),
        confidence=confidence,
        blockers=blockers,
        metadata={'decision_status': transition_decision.decision_status},
    )

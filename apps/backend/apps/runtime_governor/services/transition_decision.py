from __future__ import annotations

from apps.runtime_governor.models import (
    RuntimeModeStabilityReview,
    RuntimeModeStabilityReviewType,
    RuntimeModeTransitionDecision,
    RuntimeModeTransitionDecisionStatus,
    RuntimeModeTransitionDecisionType,
    RuntimeModeTransitionSnapshot,
)


def build_runtime_mode_transition_decision(
    *,
    transition_snapshot: RuntimeModeTransitionSnapshot,
    stability_review: RuntimeModeStabilityReview,
) -> RuntimeModeTransitionDecision:
    reason_codes = list(dict.fromkeys((transition_snapshot.reason_codes or []) + (stability_review.reason_codes or [])))
    metadata = {
        'review_type': stability_review.review_type,
        'review_severity': stability_review.review_severity,
    }

    hard_block_escalation = transition_snapshot.target_mode == 'BLOCKED' and (
        'hard_block' in ' '.join(reason_codes).lower()
        or transition_snapshot.feedback_pressure_state == 'CRITICAL'
    )

    decision_type = RuntimeModeTransitionDecisionType.ALLOW_MODE_SWITCH
    decision_status = RuntimeModeTransitionDecisionStatus.PROPOSED
    auto_applicable = True
    decision_summary = 'Transition can proceed under stabilization rules.'

    if transition_snapshot.linked_feedback_decision and transition_snapshot.linked_feedback_decision.decision_type == 'REQUIRE_MANUAL_RUNTIME_REVIEW':
        decision_type = RuntimeModeTransitionDecisionType.REQUIRE_MANUAL_STABILITY_REVIEW
        decision_status = RuntimeModeTransitionDecisionStatus.BLOCKED
        auto_applicable = False
        reason_codes.append('manual_feedback_review_required')
        decision_summary = 'Upstream feedback already requires manual review.'
    elif hard_block_escalation:
        decision_type = RuntimeModeTransitionDecisionType.ALLOW_MODE_SWITCH
        decision_status = RuntimeModeTransitionDecisionStatus.PROPOSED
        auto_applicable = True
        reason_codes.append('hard_block_escalation_allow')
        decision_summary = 'Hard-block escalation is allowed immediately and is not delayed by dwell.'
    elif stability_review.review_type == RuntimeModeStabilityReviewType.FLAPPING_RISK:
        decision_type = RuntimeModeTransitionDecisionType.BLOCK_MODE_SWITCH
        decision_status = RuntimeModeTransitionDecisionStatus.BLOCKED
        auto_applicable = False
        decision_summary = 'Flapping risk is critical; block unstable transition.'
    elif stability_review.review_type == RuntimeModeStabilityReviewType.EARLY_RELAX_ATTEMPT:
        decision_type = RuntimeModeTransitionDecisionType.DEFER_MODE_SWITCH
        decision_status = RuntimeModeTransitionDecisionStatus.SKIPPED
        auto_applicable = False
        decision_summary = 'Relaxation is deferred until additional dwell time is observed.'
    elif stability_review.review_type == RuntimeModeStabilityReviewType.INSUFFICIENT_DWELL_TIME:
        decision_type = RuntimeModeTransitionDecisionType.KEEP_CURRENT_MODE_FOR_DWELL
        decision_status = RuntimeModeTransitionDecisionStatus.SKIPPED
        auto_applicable = False
        decision_summary = 'Keep current mode to satisfy dwell requirement.'

    return RuntimeModeTransitionDecision.objects.create(
        linked_transition_snapshot=transition_snapshot,
        linked_stability_review=stability_review,
        decision_type=decision_type,
        decision_status=decision_status,
        auto_applicable=auto_applicable,
        decision_summary=decision_summary,
        reason_codes=list(dict.fromkeys(reason_codes)),
        metadata=metadata,
    )

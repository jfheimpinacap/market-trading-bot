from __future__ import annotations

from apps.runtime_governor.models import (
    RuntimeFeedbackDecision,
    RuntimeFeedbackRecommendation,
    RuntimeFeedbackRecommendationType,
    RuntimeFeedbackRun,
)


def emit_runtime_feedback_recommendation(*, feedback_run: RuntimeFeedbackRun, decision: RuntimeFeedbackDecision) -> RuntimeFeedbackRecommendation:
    recommendation_type = RuntimeFeedbackRecommendationType.KEEP_RUNTIME_STABLE
    rationale = 'Recent runtime signals are stable enough to keep current global behavior.'
    confidence = 0.68

    mapping = {
        'SHIFT_TO_MORE_CONSERVATIVE_MODE': (
            RuntimeFeedbackRecommendationType.SHIFT_TO_CONSERVATIVE_BEHAVIOR,
            'Conservative shift recommended to reduce runtime pressure without abrupt hard blocking.',
            0.72,
        ),
        'SHIFT_TO_MONITOR_ONLY': (
            RuntimeFeedbackRecommendationType.ENTER_MONITOR_ONLY_TEMPORARILY,
            'Monitor-only period recommended because opportunity flow is currently quiet.',
            0.67,
        ),
        'ENTER_RECOVERY_MODE': (
            RuntimeFeedbackRecommendationType.ENTER_RECOVERY_MODE_FOR_LOSS_PRESSURE,
            'Recovery mode recommended to absorb repeated recent losses safely.',
            0.8,
        ),
        'REDUCE_ADMISSION_AND_CADENCE': (
            RuntimeFeedbackRecommendationType.REDUCE_ADMISSION_AND_CADENCE_NOW,
            'Admission and cadence reduction recommended due to blocked/parked saturation pressure.',
            0.74,
        ),
        'REQUIRE_MANUAL_RUNTIME_REVIEW': (
            RuntimeFeedbackRecommendationType.REQUIRE_MANUAL_RUNTIME_REVIEW,
            'Manual runtime review recommended before any further global posture adjustments.',
            0.9,
        ),
        'RELAX_TO_CAUTION': (
            RuntimeFeedbackRecommendationType.SHIFT_TO_CONSERVATIVE_BEHAVIOR,
            'Runtime has stabilized enough to relax from recovery into caution conservatively.',
            0.63,
        ),
    }
    if decision.decision_type in mapping:
        recommendation_type, rationale, confidence = mapping[decision.decision_type]

    blockers = []
    if decision.decision_type == 'REQUIRE_MANUAL_RUNTIME_REVIEW':
        blockers.append('manual_review_required_before_apply')

    return RuntimeFeedbackRecommendation.objects.create(
        recommendation_type=recommendation_type,
        target_feedback_run=feedback_run,
        target_diagnostic_review=decision.linked_diagnostic_review,
        target_feedback_decision=decision,
        rationale=rationale,
        reason_codes=decision.reason_codes,
        confidence=confidence,
        blockers=blockers,
        metadata={'decision_type': decision.decision_type},
    )

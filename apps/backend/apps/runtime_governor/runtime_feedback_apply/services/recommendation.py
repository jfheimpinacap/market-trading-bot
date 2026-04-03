from __future__ import annotations

from apps.runtime_governor.models import (
    RuntimeFeedbackApplyDecision,
    RuntimeFeedbackApplyRecommendation,
    RuntimeFeedbackApplyRecommendationType,
)


def emit_apply_recommendations(*, apply_decision: RuntimeFeedbackApplyDecision) -> list[RuntimeFeedbackApplyRecommendation]:
    recommendations: list[RuntimeFeedbackApplyRecommendation] = []

    if apply_decision.apply_type == 'APPLY_MANUAL_REVIEW_ONLY':
        recommendations.append(
            RuntimeFeedbackApplyRecommendation.objects.create(
                recommendation_type=RuntimeFeedbackApplyRecommendationType.REQUIRE_MANUAL_FEEDBACK_APPLY_REVIEW,
                target_feedback_decision=apply_decision.linked_feedback_decision,
                target_apply_decision=apply_decision,
                rationale='Apply mapping is ambiguous or conflicts with safety posture, requiring manual confirmation.',
                reason_codes=apply_decision.reason_codes,
                confidence=0.95,
                blockers=['manual_review_required'],
            )
        )
        recommendations.append(
            RuntimeFeedbackApplyRecommendation.objects.create(
                recommendation_type=RuntimeFeedbackApplyRecommendationType.BLOCK_AUTOMATIC_FEEDBACK_APPLY,
                target_feedback_decision=apply_decision.linked_feedback_decision,
                target_apply_decision=apply_decision,
                rationale='Automatic apply is conservatively blocked until operator review is completed.',
                reason_codes=['auto_apply_blocked'],
                confidence=0.9,
                blockers=['manual_review_required'],
            )
        )
        return recommendations

    if apply_decision.apply_type == 'APPLY_KEEP_CURRENT_MODE':
        recommendations.append(
            RuntimeFeedbackApplyRecommendation.objects.create(
                recommendation_type=RuntimeFeedbackApplyRecommendationType.KEEP_AS_ADVISORY_ONLY,
                target_feedback_decision=apply_decision.linked_feedback_decision,
                target_apply_decision=apply_decision,
                rationale='Feedback is retained as advisory because no conservative mode shift is required.',
                reason_codes=['no_mode_change_required'],
                confidence=0.85,
                blockers=[],
            )
        )
        return recommendations

    recommendations.append(
        RuntimeFeedbackApplyRecommendation.objects.create(
            recommendation_type=RuntimeFeedbackApplyRecommendationType.APPLY_FEEDBACK_NOW,
            target_feedback_decision=apply_decision.linked_feedback_decision,
            target_apply_decision=apply_decision,
            rationale='Feedback decision is clear and can be applied conservatively to global operating mode.',
            reason_codes=apply_decision.reason_codes,
            confidence=0.8,
            blockers=[],
        )
    )

    if apply_decision.current_mode != apply_decision.target_mode:
        recommendations.append(
            RuntimeFeedbackApplyRecommendation.objects.create(
                recommendation_type=RuntimeFeedbackApplyRecommendationType.REFRESH_ENFORCEMENT_AFTER_MODE_SWITCH,
                target_feedback_decision=apply_decision.linked_feedback_decision,
                target_apply_decision=apply_decision,
                rationale='A mode switch requires a downstream enforcement refresh for timing/admission/exposure/execution/recovery modules.',
                reason_codes=['mode_switch_requires_enforcement_refresh'],
                confidence=0.88,
                blockers=[],
            )
        )

    return recommendations

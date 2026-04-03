from __future__ import annotations

from collections import Counter

from django.utils import timezone

from apps.runtime_governor.models import (
    RuntimeFeedbackDecision,
    RuntimeModeTransitionApplyRecord,
    RuntimeModeStabilizationRecommendation,
    RuntimeModeStabilizationRun,
    RuntimeModeTransitionDecision,
    RuntimeModeTransitionDecisionType,
    RuntimeModeTransitionSnapshot,
    RuntimeModeStabilityReview,
)
from apps.runtime_governor.services.apply_transition import apply_stabilized_transition_decision
from apps.runtime_governor.services.recommendation import emit_runtime_mode_stabilization_recommendation
from apps.runtime_governor.services.stability_review import build_runtime_mode_stability_review
from apps.runtime_governor.services.transition_decision import build_runtime_mode_transition_decision
from apps.runtime_governor.services.transition_snapshot import build_runtime_mode_transition_snapshot

FEEDBACK_DECISION_TARGET_MODE = {
    'KEEP_CURRENT_GLOBAL_MODE': None,
    'SHIFT_TO_MORE_CONSERVATIVE_MODE': 'CAUTION',
    'SHIFT_TO_MONITOR_ONLY': 'MONITOR_ONLY',
    'ENTER_RECOVERY_MODE': 'RECOVERY_MODE',
    'RELAX_TO_CAUTION': 'CAUTION',
    'REDUCE_ADMISSION_AND_CADENCE': 'CAUTION',
    'REQUIRE_MANUAL_RUNTIME_REVIEW': None,
}


def run_mode_stabilization_review(*, triggered_by: str = 'operator-ui', auto_apply_safe: bool = False) -> dict:
    run = RuntimeModeStabilizationRun.objects.create(metadata={'triggered_by': triggered_by, 'auto_apply_safe': auto_apply_safe})

    feedback_decisions = RuntimeFeedbackDecision.objects.select_related('linked_performance_snapshot').order_by('-created_at', '-id')[:20]
    snapshots: list[RuntimeModeTransitionSnapshot] = []
    reviews: list[RuntimeModeStabilityReview] = []
    decisions: list[RuntimeModeTransitionDecision] = []
    recommendations: list[RuntimeModeStabilizationRecommendation] = []
    apply_records: list[RuntimeModeTransitionApplyRecord] = []

    for feedback_decision in feedback_decisions:
        target_mode = FEEDBACK_DECISION_TARGET_MODE.get(feedback_decision.decision_type)
        if feedback_decision.linked_performance_snapshot.runtime_pressure_state == 'CRITICAL' and (
            'hard_block' in ' '.join(feedback_decision.reason_codes or []).lower()
            or feedback_decision.linked_performance_snapshot.metadata.get('safety_posture') == 'HARD_BLOCK'
        ):
            target_mode = 'BLOCKED'
        if not target_mode:
            continue
        snapshot = build_runtime_mode_transition_snapshot(
            run_id=run.id,
            feedback_decision=feedback_decision,
            target_mode=target_mode,
        )
        review = build_runtime_mode_stability_review(transition_snapshot=snapshot)
        decision = build_runtime_mode_transition_decision(
            transition_snapshot=snapshot,
            stability_review=review,
        )
        recommendation = emit_runtime_mode_stabilization_recommendation(transition_decision=decision)

        snapshots.append(snapshot)
        reviews.append(review)
        decisions.append(decision)
        recommendations.append(recommendation)
        if auto_apply_safe and decision.auto_applicable and decision.decision_type == RuntimeModeTransitionDecisionType.ALLOW_MODE_SWITCH:
            apply_result = apply_stabilized_transition_decision(
                transition_decision=decision,
                triggered_by='mode-stabilization-auto-safe',
                auto_apply_safe=True,
            )
            apply_records.append(apply_result.apply_record)

    decision_counts = Counter(decision.decision_type for decision in decisions)

    run.considered_transition_count = len(decisions)
    run.allowed_count = decision_counts.get(RuntimeModeTransitionDecisionType.ALLOW_MODE_SWITCH, 0)
    run.deferred_count = decision_counts.get(RuntimeModeTransitionDecisionType.DEFER_MODE_SWITCH, 0)
    run.dwell_hold_count = decision_counts.get(RuntimeModeTransitionDecisionType.KEEP_CURRENT_MODE_FOR_DWELL, 0)
    run.blocked_count = decision_counts.get(RuntimeModeTransitionDecisionType.BLOCK_MODE_SWITCH, 0)
    run.manual_review_count = decision_counts.get(RuntimeModeTransitionDecisionType.REQUIRE_MANUAL_STABILITY_REVIEW, 0)
    run.recommendation_summary = {
        'recommendation_count': len(recommendations),
        'latest_recommendation_type': recommendations[0].recommendation_type if recommendations else None,
        'decision_counts': dict(decision_counts),
        'apply_record_count': len(apply_records),
    }
    run.metadata = {
        **(run.metadata or {}),
        'transition_snapshot_ids': [snapshot.id for snapshot in snapshots],
        'stability_review_ids': [review.id for review in reviews],
        'transition_decision_ids': [decision.id for decision in decisions],
        'recommendation_ids': [recommendation.id for recommendation in recommendations],
        'apply_record_ids': [record.id for record in apply_records],
    }
    run.completed_at = timezone.now()
    run.save()

    return {
        'run': run,
        'snapshots': snapshots,
        'reviews': reviews,
        'decisions': decisions,
        'recommendations': recommendations,
        'apply_records': apply_records,
    }


def get_mode_stabilization_summary() -> dict:
    latest_run = RuntimeModeStabilizationRun.objects.order_by('-started_at', '-id').first()
    latest_snapshot = RuntimeModeTransitionSnapshot.objects.order_by('-created_at', '-id').first()
    latest_review = RuntimeModeStabilityReview.objects.order_by('-created_at', '-id').first()
    latest_decision = RuntimeModeTransitionDecision.objects.order_by('-created_at', '-id').first()
    latest_apply_record = RuntimeModeTransitionApplyRecord.objects.order_by('-created_at', '-id').first()

    return {
        'latest_run_id': latest_run.id if latest_run else None,
        'latest_snapshot_id': latest_snapshot.id if latest_snapshot else None,
        'latest_review_id': latest_review.id if latest_review else None,
        'latest_decision_id': latest_decision.id if latest_decision else None,
        'latest_apply_record_id': latest_apply_record.id if latest_apply_record else None,
        'runs': RuntimeModeStabilizationRun.objects.count(),
        'snapshots': RuntimeModeTransitionSnapshot.objects.count(),
        'reviews': RuntimeModeStabilityReview.objects.count(),
        'decisions': RuntimeModeTransitionDecision.objects.count(),
        'recommendations': RuntimeModeStabilizationRecommendation.objects.count(),
        'apply_records': RuntimeModeTransitionApplyRecord.objects.count(),
        'allowed_count': RuntimeModeTransitionDecision.objects.filter(decision_type='ALLOW_MODE_SWITCH').count(),
        'deferred_count': RuntimeModeTransitionDecision.objects.filter(decision_type='DEFER_MODE_SWITCH').count(),
        'dwell_hold_count': RuntimeModeTransitionDecision.objects.filter(decision_type='KEEP_CURRENT_MODE_FOR_DWELL').count(),
        'blocked_count': RuntimeModeTransitionDecision.objects.filter(decision_type='BLOCK_MODE_SWITCH').count(),
        'manual_review_count': RuntimeModeTransitionDecision.objects.filter(decision_type='REQUIRE_MANUAL_STABILITY_REVIEW').count(),
        'applied_count': RuntimeModeTransitionApplyRecord.objects.filter(apply_status='APPLIED').count(),
        'blocked_apply_count': RuntimeModeTransitionApplyRecord.objects.filter(apply_status='BLOCKED').count(),
        'recommendation_summary': latest_run.recommendation_summary if latest_run else {},
    }

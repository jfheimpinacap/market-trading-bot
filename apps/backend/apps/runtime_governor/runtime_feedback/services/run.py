from __future__ import annotations

from collections import Counter

from django.utils import timezone

from apps.runtime_governor.models import (
    RuntimeFeedbackDecision,
    RuntimeFeedbackDecisionStatus,
    RuntimeFeedbackDecisionType,
    RuntimeFeedbackRecommendation,
    RuntimeFeedbackRun,
)
from apps.runtime_governor.runtime_feedback.services.diagnostics import build_runtime_diagnostic_review
from apps.runtime_governor.runtime_feedback.services.feedback import build_runtime_feedback_decision
from apps.runtime_governor.runtime_feedback.services.performance import build_runtime_performance_snapshot
from apps.runtime_governor.runtime_feedback.services.recommendation import emit_runtime_feedback_recommendation


def _apply_runtime_feedback_decision(*, decision: RuntimeFeedbackDecision):
    if decision.decision_type == RuntimeFeedbackDecisionType.REQUIRE_MANUAL_RUNTIME_REVIEW:
        decision.decision_status = RuntimeFeedbackDecisionStatus.BLOCKED
        decision.save(update_fields=['decision_status', 'updated_at'])
        return None

    target_mode_map = {
        RuntimeFeedbackDecisionType.KEEP_CURRENT_GLOBAL_MODE: decision.linked_performance_snapshot.current_global_mode,
        RuntimeFeedbackDecisionType.SHIFT_TO_MORE_CONSERVATIVE_MODE: 'CAUTION',
        RuntimeFeedbackDecisionType.SHIFT_TO_MONITOR_ONLY: 'MONITOR_ONLY',
        RuntimeFeedbackDecisionType.ENTER_RECOVERY_MODE: 'RECOVERY_MODE',
        RuntimeFeedbackDecisionType.RELAX_TO_CAUTION: 'CAUTION',
        RuntimeFeedbackDecisionType.REDUCE_ADMISSION_AND_CADENCE: 'THROTTLED',
    }
    target_mode = target_mode_map.get(decision.decision_type)
    if not target_mode:
        decision.decision_status = RuntimeFeedbackDecisionStatus.SKIPPED
        decision.save(update_fields=['decision_status', 'updated_at'])
        return None

    decision.decision_status = RuntimeFeedbackDecisionStatus.APPLIED
    decision.metadata = {
        **(decision.metadata or {}),
        'operating_mode_input_target': target_mode,
        'next_step': 'consume_via_operating_mode_review',
    }
    decision.save(update_fields=['decision_status', 'metadata', 'updated_at'])
    return target_mode


def run_runtime_feedback_review(*, triggered_by: str = 'operator-ui', auto_apply: bool = False) -> dict:
    feedback_run = RuntimeFeedbackRun.objects.create(metadata={'triggered_by': triggered_by, 'auto_apply': auto_apply})
    snapshot = build_runtime_performance_snapshot(feedback_run=feedback_run)
    diagnostic = build_runtime_diagnostic_review(snapshot=snapshot)
    decision = build_runtime_feedback_decision(snapshot=snapshot, diagnostic=diagnostic)
    recommendation = emit_runtime_feedback_recommendation(feedback_run=feedback_run, decision=decision)

    if auto_apply and decision.auto_applicable:
        _apply_runtime_feedback_decision(decision=decision)

    feedback_run.considered_metric_count = 10
    feedback_run.healthy_runtime_count = 1 if diagnostic.diagnostic_type == 'HEALTHY_RUNTIME' else 0
    feedback_run.overtrading_alert_count = 1 if diagnostic.diagnostic_type == 'OVERTRADING_PRESSURE' else 0
    feedback_run.quiet_runtime_alert_count = 1 if diagnostic.diagnostic_type == 'QUIET_RUNTIME' else 0
    feedback_run.loss_pressure_alert_count = 1 if diagnostic.diagnostic_type == 'LOSS_RECOVERY_PRESSURE' else 0
    feedback_run.blocked_runtime_alert_count = 1 if diagnostic.diagnostic_type == 'BLOCKED_RUNTIME_SATURATION' else 0
    feedback_run.feedback_decision_count = 1
    feedback_run.recommendation_summary = {
        'diagnostic_type': diagnostic.diagnostic_type,
        'decision_type': decision.decision_type,
        'decision_status': decision.decision_status,
        'recommendation_type': recommendation.recommendation_type,
    }
    feedback_run.completed_at = timezone.now()
    feedback_run.metadata = {
        **(feedback_run.metadata or {}),
        'performance_snapshot_id': snapshot.id,
        'diagnostic_review_id': diagnostic.id,
        'feedback_decision_id': decision.id,
        'recommendation_id': recommendation.id,
    }
    feedback_run.save()

    return {
        'run': feedback_run,
        'snapshot': snapshot,
        'diagnostic': diagnostic,
        'decision': decision,
        'recommendation': recommendation,
    }


def get_runtime_feedback_summary() -> dict:
    latest_run = RuntimeFeedbackRun.objects.order_by('-started_at', '-id').first()
    latest_snapshot = latest_run.performance_snapshots.order_by('-created_at', '-id').first() if latest_run else None
    latest_decision = RuntimeFeedbackDecision.objects.order_by('-created_at', '-id').first()

    decision_counts = Counter(RuntimeFeedbackDecision.objects.values_list('decision_type', flat=True))
    status_counts = Counter(RuntimeFeedbackDecision.objects.values_list('decision_status', flat=True))

    return {
        'latest_run_id': latest_run.id if latest_run else None,
        'latest_snapshot_id': latest_snapshot.id if latest_snapshot else None,
        'latest_decision_id': latest_decision.id if latest_decision else None,
        'current_mode': latest_snapshot.current_global_mode if latest_snapshot else 'BALANCED',
        'recent_dispatches': latest_snapshot.recent_dispatch_count if latest_snapshot else 0,
        'recent_losses': latest_snapshot.recent_loss_count if latest_snapshot else 0,
        'no_action_pressure': latest_snapshot.recent_no_action_tick_count if latest_snapshot else 0,
        'blocked_pressure': latest_snapshot.recent_blocked_tick_count if latest_snapshot else 0,
        'feedback_runs': RuntimeFeedbackRun.objects.count(),
        'feedback_decisions': RuntimeFeedbackDecision.objects.count(),
        'applied_decisions': status_counts.get(RuntimeFeedbackDecisionStatus.APPLIED, 0),
        'manual_review_required': decision_counts.get(RuntimeFeedbackDecisionType.REQUIRE_MANUAL_RUNTIME_REVIEW, 0),
        'recommendation_summary': latest_run.recommendation_summary if latest_run else {},
    }


def apply_runtime_feedback_decision(*, decision: RuntimeFeedbackDecision):
    return _apply_runtime_feedback_decision(decision=decision)

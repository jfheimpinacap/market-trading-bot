from __future__ import annotations

from collections import Counter

from django.utils import timezone

from apps.runtime_governor.models import (
    GlobalOperatingMode,
    GlobalOperatingModeDecision,
    GlobalOperatingModeDecisionStatus,
    GlobalRuntimePostureRun,
)
from apps.runtime_governor.services.operating_mode.mode_switch import decide_and_optionally_apply_mode
from apps.runtime_governor.services.operating_mode.posture import build_posture_snapshot
from apps.runtime_governor.services.operating_mode.recommendation import emit_mode_recommendation


def run_operating_mode_review(*, triggered_by: str = 'operator-ui', auto_apply: bool = True) -> dict:
    posture_run = GlobalRuntimePostureRun.objects.create(metadata={'triggered_by': triggered_by, 'auto_apply': auto_apply})
    snapshot = build_posture_snapshot(posture_run=posture_run)
    mode_review = decide_and_optionally_apply_mode(snapshot=snapshot, auto_apply=auto_apply)
    recommendation = emit_mode_recommendation(decision=mode_review.decision)

    posture_run.considered_signal_count = len(snapshot.reason_codes) if snapshot.reason_codes else 1
    posture_run.mode_kept_count = 1 if mode_review.decision.decision_type == 'KEEP_CURRENT_MODE' else 0
    posture_run.mode_switch_count = 1 if mode_review.switch_record.switch_status == 'APPLIED' else 0
    posture_run.caution_count = 1 if mode_review.decision.target_mode == GlobalOperatingMode.CAUTION else 0
    posture_run.monitor_only_count = 1 if mode_review.decision.target_mode == GlobalOperatingMode.MONITOR_ONLY else 0
    posture_run.recovery_mode_count = 1 if mode_review.decision.target_mode == GlobalOperatingMode.RECOVERY_MODE else 0
    posture_run.throttled_count = 1 if mode_review.decision.target_mode == GlobalOperatingMode.THROTTLED else 0
    posture_run.blocked_count = 1 if mode_review.decision.target_mode == GlobalOperatingMode.BLOCKED else 0
    posture_run.completed_at = timezone.now()
    posture_run.recommendation_summary = {
        'type': recommendation.recommendation_type,
        'decision_status': mode_review.decision.decision_status,
    }
    posture_run.metadata = {
        **(posture_run.metadata or {}),
        'snapshot_id': snapshot.id,
        'decision_id': mode_review.decision.id,
        'switch_record_id': mode_review.switch_record.id,
        'recommendation_id': recommendation.id,
    }
    posture_run.save()

    return {
        'run': posture_run,
        'snapshot': snapshot,
        'decision': mode_review.decision,
        'switch_record': mode_review.switch_record,
        'recommendation': recommendation,
    }


def get_operating_mode_summary() -> dict:
    latest_run = GlobalRuntimePostureRun.objects.order_by('-started_at', '-id').first()
    latest_decision = GlobalOperatingModeDecision.objects.order_by('-created_at_decision', '-id').first()

    decision_counts = Counter(
        GlobalOperatingModeDecision.objects.values_list('target_mode', flat=True)
    )
    status_counts = Counter(
        GlobalOperatingModeDecision.objects.values_list('decision_status', flat=True)
    )

    return {
        'latest_run_id': latest_run.id if latest_run else None,
        'latest_decision_id': latest_decision.id if latest_decision else None,
        'active_mode': latest_decision.target_mode if latest_decision else GlobalOperatingMode.BALANCED,
        'posture_reviews': GlobalRuntimePostureRun.objects.count(),
        'mode_kept': status_counts.get(GlobalOperatingModeDecisionStatus.SKIPPED, 0) + status_counts.get(GlobalOperatingModeDecisionStatus.PROPOSED, 0),
        'mode_switched': status_counts.get(GlobalOperatingModeDecisionStatus.APPLIED, 0),
        'caution_count': decision_counts.get(GlobalOperatingMode.CAUTION, 0),
        'monitor_only_count': decision_counts.get(GlobalOperatingMode.MONITOR_ONLY, 0),
        'recovery_mode_count': decision_counts.get(GlobalOperatingMode.RECOVERY_MODE, 0),
        'throttled_count': decision_counts.get(GlobalOperatingMode.THROTTLED, 0),
        'blocked_count': decision_counts.get(GlobalOperatingMode.BLOCKED, 0),
        'recommendation_summary': latest_run.recommendation_summary if latest_run else {},
    }

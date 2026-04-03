from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from apps.runtime_governor.models import (
    RuntimeFeedbackApplyRecord,
    RuntimeFeedbackDecision,
    RuntimeModeFeedbackPressureState,
    RuntimeModeTransitionRiskState,
    RuntimeModeTransitionSnapshot,
)
from apps.runtime_governor.services.operating_mode.mode_switch import get_active_global_operating_mode
from apps.runtime_governor.services.state import get_runtime_state

RELAXATION_TARGETS = {'BALANCED', 'CAUTION', 'MONITOR_ONLY'}
CONSERVATIVE_LEVELS = {
    'BALANCED': 0,
    'CAUTION': 1,
    'MONITOR_ONLY': 2,
    'THROTTLED': 3,
    'RECOVERY_MODE': 4,
    'BLOCKED': 5,
}


def _pressure_state_from_feedback_decision(feedback_decision: RuntimeFeedbackDecision | None) -> str:
    if not feedback_decision:
        return RuntimeModeFeedbackPressureState.NORMAL
    pressure = (feedback_decision.linked_performance_snapshot.runtime_pressure_state or 'NORMAL').upper()
    if pressure == 'CRITICAL':
        return RuntimeModeFeedbackPressureState.CRITICAL
    if pressure == 'HIGH':
        return RuntimeModeFeedbackPressureState.HIGH
    if pressure == 'CAUTION':
        return RuntimeModeFeedbackPressureState.NORMAL
    return RuntimeModeFeedbackPressureState.LOW


def _is_relaxation(*, current_mode: str, target_mode: str) -> bool:
    return CONSERVATIVE_LEVELS.get(target_mode, 0) < CONSERVATIVE_LEVELS.get(current_mode, 0)


def _risk_state(*, recent_switch_count: int, time_in_current_mode_seconds: int, is_relaxation: bool) -> str:
    if recent_switch_count >= 4:
        return RuntimeModeTransitionRiskState.CRITICAL
    if recent_switch_count >= 2:
        return RuntimeModeTransitionRiskState.HIGH
    if is_relaxation and time_in_current_mode_seconds < 900:
        return RuntimeModeTransitionRiskState.HIGH
    if time_in_current_mode_seconds < 300:
        return RuntimeModeTransitionRiskState.CAUTION
    return RuntimeModeTransitionRiskState.LOW


def build_runtime_mode_transition_snapshot(
    *,
    run_id: int | None,
    feedback_decision: RuntimeFeedbackDecision,
    target_mode: str,
    recent_switch_window_seconds: int = 1800,
) -> RuntimeModeTransitionSnapshot:
    now = timezone.now()
    current_mode = get_active_global_operating_mode()
    state = get_runtime_state()

    recent_switches = RuntimeFeedbackApplyRecord.objects.filter(
        record_status='APPLIED',
        metadata__mode_switched=True,
        created_at__gte=now - timedelta(seconds=recent_switch_window_seconds),
    ).order_by('-created_at', '-id')
    last_switch = RuntimeFeedbackApplyRecord.objects.filter(
        record_status='APPLIED',
        metadata__mode_switched=True,
    ).order_by('-created_at', '-id').first()

    if last_switch and last_switch.applied_mode == current_mode:
        current_mode_started_at = last_switch.created_at
    else:
        current_mode_started_at = state.updated_at

    time_in_current_mode_seconds = max(int((now - current_mode_started_at).total_seconds()), 0)
    recent_switch_count = recent_switches.count()
    is_relaxation = _is_relaxation(current_mode=current_mode, target_mode=target_mode)
    reason_codes = list(dict.fromkeys((feedback_decision.reason_codes or []) + [feedback_decision.decision_type.lower()]))
    if is_relaxation:
        reason_codes.append('relaxation_attempt')
    if recent_switch_count >= 2:
        reason_codes.append('recent_switches_detected')

    risk_state = _risk_state(
        recent_switch_count=recent_switch_count,
        time_in_current_mode_seconds=time_in_current_mode_seconds,
        is_relaxation=is_relaxation,
    )

    summary = (
        f'Mode stabilization snapshot: {current_mode} -> {target_mode}, '
        f'{recent_switch_count} switch(es) in {recent_switch_window_seconds}s, '
        f'dwell {time_in_current_mode_seconds}s.'
    )

    return RuntimeModeTransitionSnapshot.objects.create(
        linked_run_id=run_id,
        linked_feedback_decision=feedback_decision,
        current_mode=current_mode,
        target_mode=target_mode,
        current_mode_started_at=current_mode_started_at,
        time_in_current_mode_seconds=time_in_current_mode_seconds,
        recent_switch_count=recent_switch_count,
        recent_switch_window_seconds=recent_switch_window_seconds,
        last_switch_at=last_switch.created_at if last_switch else None,
        feedback_pressure_state=_pressure_state_from_feedback_decision(feedback_decision),
        transition_risk_state=risk_state,
        snapshot_summary=summary,
        reason_codes=reason_codes,
        metadata={
            'feedback_decision_id': feedback_decision.id,
            'feedback_decision_type': feedback_decision.decision_type,
            'is_relaxation': is_relaxation,
        },
    )

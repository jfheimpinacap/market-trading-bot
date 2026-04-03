from __future__ import annotations

from datetime import timedelta

from django.utils import timezone
from django.db.models import Sum

from apps.autonomous_trader.models import AutonomousDispatchRecord, AutonomousDispatchStatus, AutonomousTradeOutcome, AutonomousOutcomeStatus, AutonomousOutcomeType
from apps.mission_control.governance_backlog_pressure.services.run import governance_backlog_pressure_summary
from apps.mission_control.models import (
    AutonomousResumeDecision,
    AutonomousResumeDecisionType,
    AutonomousRuntimeTick,
    AutonomousRuntimeTickStatus,
    AutonomousSessionHealthSnapshot,
    AutonomousSessionAdmissionDecision,
    AutonomousSessionAdmissionDecisionType,
)
from apps.portfolio_governor.models import PortfolioExposureDecision, PortfolioExposureDecisionType
from apps.runtime_governor.models import RuntimePerformanceSnapshot, RuntimePressureState, SignalQualityState
from apps.runtime_governor.services.operating_mode import get_active_global_operating_mode

WINDOW_HOURS = 12


def _signal_quality(*, dispatch_count: int, loss_count: int, no_action_ticks: int) -> str:
    if dispatch_count == 0 and no_action_ticks >= 3:
        return SignalQualityState.QUIET
    if dispatch_count >= 6 and loss_count == 0:
        return SignalQualityState.STRONG
    if loss_count >= max(2, dispatch_count // 2):
        return SignalQualityState.WEAK
    return SignalQualityState.NORMAL


def _runtime_pressure(*, loss_count: int, blocked_ticks: int, parked_sessions: int, throttle_count: int) -> str:
    pressure_score = (loss_count * 2) + blocked_ticks + parked_sessions + throttle_count
    if pressure_score >= 8:
        return RuntimePressureState.CRITICAL
    if pressure_score >= 5:
        return RuntimePressureState.HIGH
    if pressure_score >= 2:
        return RuntimePressureState.CAUTION
    return RuntimePressureState.NORMAL


def build_runtime_performance_snapshot(*, feedback_run=None) -> RuntimePerformanceSnapshot:
    since = timezone.now() - timedelta(hours=WINDOW_HOURS)

    recent_dispatch_count = AutonomousDispatchRecord.objects.filter(
        created_at__gte=since,
        dispatch_status__in=[AutonomousDispatchStatus.DISPATCHED, AutonomousDispatchStatus.FILLED, AutonomousDispatchStatus.PARTIAL],
    ).count()
    recent_deferred_dispatch_count = AutonomousDispatchRecord.objects.filter(
        created_at__gte=since,
        dispatch_status=AutonomousDispatchStatus.SKIPPED,
    ).count()

    recent_closed_outcome_count = AutonomousTradeOutcome.objects.filter(
        created_at__gte=since,
        outcome_status=AutonomousOutcomeStatus.CLOSED,
    ).count()
    closed_loss_count = AutonomousTradeOutcome.objects.filter(
        created_at__gte=since,
        outcome_status=AutonomousOutcomeStatus.CLOSED,
        outcome_type=AutonomousOutcomeType.LOSS_EXIT,
    ).count()
    health_loss_count = AutonomousSessionHealthSnapshot.objects.filter(
        created_at__gte=since,
        recent_loss_count__gte=1,
    ).aggregate(total=Sum('recent_loss_count'))['total'] or 0
    recent_loss_count = max(closed_loss_count, health_loss_count)

    recent_no_action_tick_count = AutonomousRuntimeTick.objects.filter(
        created_at__gte=since,
        tick_status=AutonomousRuntimeTickStatus.SKIPPED,
    ).count()
    recent_blocked_tick_count = AutonomousRuntimeTick.objects.filter(
        created_at__gte=since,
        tick_status=AutonomousRuntimeTickStatus.BLOCKED,
    ).count()

    recent_parked_session_count = AutonomousSessionAdmissionDecision.objects.filter(
        created_at__gte=since,
        decision_type=AutonomousSessionAdmissionDecisionType.PARK_SESSION,
    ).count()

    recent_exposure_throttle_count = PortfolioExposureDecision.objects.filter(
        created_at__gte=since,
        decision_type__in=[PortfolioExposureDecisionType.THROTTLE_NEW_ENTRIES, PortfolioExposureDecisionType.PAUSE_CLUSTER_ACTIVITY],
    ).count()

    recent_recovery_resume_count = AutonomousResumeDecision.objects.filter(
        created_at__gte=since,
        decision_type__in=[AutonomousResumeDecisionType.READY_TO_RESUME, AutonomousResumeDecisionType.RESUME_IN_MONITOR_ONLY_MODE],
    ).count()
    governance_backlog_pressure_state = str(
        governance_backlog_pressure_summary().get('governance_backlog_pressure_state') or 'NORMAL'
    ).upper()

    signal_quality_state = _signal_quality(
        dispatch_count=recent_dispatch_count,
        loss_count=recent_loss_count,
        no_action_ticks=recent_no_action_tick_count,
    )
    runtime_pressure_state = _runtime_pressure(
        loss_count=recent_loss_count,
        blocked_ticks=recent_blocked_tick_count,
        parked_sessions=recent_parked_session_count,
        throttle_count=recent_exposure_throttle_count,
    )

    reason_codes = []
    if recent_loss_count >= 2:
        reason_codes.append('loss_pressure_detected')
    if recent_no_action_tick_count >= 3:
        reason_codes.append('quiet_window_detected')
    if recent_blocked_tick_count >= 2 or recent_parked_session_count >= 2:
        reason_codes.append('blocked_or_parked_pressure_detected')
    if recent_exposure_throttle_count >= 1:
        reason_codes.append('exposure_throttle_detected')
    if recent_dispatch_count >= 8:
        reason_codes.append('high_dispatch_velocity')
    if governance_backlog_pressure_state != 'NORMAL':
        reason_codes.append(f'governance_backlog_pressure:{governance_backlog_pressure_state}')
    if not reason_codes:
        reason_codes.append('stable_runtime_window')

    snapshot_summary = (
        f'Runtime feedback window ({WINDOW_HOURS}h): dispatch={recent_dispatch_count}, closed_outcomes={recent_closed_outcome_count}, '
        f'losses={recent_loss_count}, no_action_ticks={recent_no_action_tick_count}, blocked_ticks={recent_blocked_tick_count}, '
        f'parked_sessions={recent_parked_session_count}, throttle_events={recent_exposure_throttle_count}, '
        f'governance_backlog={governance_backlog_pressure_state}.'
    )

    return RuntimePerformanceSnapshot.objects.create(
        linked_feedback_run=feedback_run,
        current_global_mode=get_active_global_operating_mode(),
        recent_dispatch_count=recent_dispatch_count,
        recent_closed_outcome_count=recent_closed_outcome_count,
        recent_loss_count=recent_loss_count,
        recent_no_action_tick_count=recent_no_action_tick_count,
        recent_blocked_tick_count=recent_blocked_tick_count,
        recent_deferred_dispatch_count=recent_deferred_dispatch_count,
        recent_parked_session_count=recent_parked_session_count,
        recent_exposure_throttle_count=recent_exposure_throttle_count,
        recent_recovery_resume_count=recent_recovery_resume_count,
        signal_quality_state=signal_quality_state,
        runtime_pressure_state=runtime_pressure_state,
        snapshot_summary=snapshot_summary,
        reason_codes=reason_codes,
        metadata={
            'window_hours': WINDOW_HOURS,
            'governance_backlog_pressure_state': governance_backlog_pressure_state,
        },
    )

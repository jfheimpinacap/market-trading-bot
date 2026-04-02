from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.utils import timezone

from apps.mission_control.models import (
    AutonomousCadenceMode,
    AutonomousCooldownState,
    AutonomousCooldownStatus,
    AutonomousHeartbeatDecisionType,
    AutonomousRuntimeSession,
    AutonomousRuntimeTickStatus,
    AutonomousSignalPressureState,
    AutonomousTimingDecision,
    AutonomousTimingDecisionStatus,
    AutonomousTimingDecisionType,
    AutonomousTimingStatus,
    AutonomousSessionTimingSnapshot,
)
from apps.mission_control.services.session_timing.profile import resolve_profile_for_session
from apps.runtime_governor.mode_enforcement.services.enforcement import get_module_enforcement_state


@dataclass
class TimingReviewResult:
    snapshot: AutonomousSessionTimingSnapshot
    decision: AutonomousTimingDecision


def _count_consecutive_ticks(session: AutonomousRuntimeSession, *, statuses: set[str], reason_codes: set[str] | None = None) -> int:
    ticks = session.ticks.order_by('-tick_index', '-id')[:20]
    count = 0
    for tick in ticks:
        tick_reasons = set(tick.reason_codes or [])
        status_match = tick.tick_status in statuses
        reason_match = bool(reason_codes and tick_reasons.intersection(reason_codes))
        if status_match or reason_match:
            count += 1
            continue
        break
    return count


def _infer_signal_pressure(*, active_cooldowns: int, recent_dispatch_count: int, consecutive_no_action: int, recent_loss_count: int) -> str:
    if recent_loss_count > 0 or active_cooldowns >= 2:
        return AutonomousSignalPressureState.LOW
    if consecutive_no_action >= 3 and recent_dispatch_count == 0:
        return AutonomousSignalPressureState.QUIET
    if recent_dispatch_count >= 2:
        return AutonomousSignalPressureState.HIGH
    return AutonomousSignalPressureState.NORMAL


def evaluate_session_timing(*, session: AutonomousRuntimeSession) -> TimingReviewResult:
    now = timezone.now()
    profile = resolve_profile_for_session(session=session)
    latest_tick = session.ticks.order_by('-tick_index', '-id').first()
    last_tick_at = latest_tick.created_at if latest_tick else session.started_at

    active_cooldowns = AutonomousCooldownState.objects.filter(
        linked_session=session,
        cooldown_status=AutonomousCooldownStatus.ACTIVE,
        expires_at__gt=now,
    ).order_by('expires_at')
    active_cooldown_count = active_cooldowns.count()

    recent_ticks = session.ticks.order_by('-created_at', '-id')[:10]
    recent_dispatch_count = sum(1 for tick in recent_ticks if tick.tick_status == AutonomousRuntimeTickStatus.COMPLETED)
    recent_loss_count = sum(1 for tick in recent_ticks if 'loss_detected' in (tick.reason_codes or []))
    consecutive_no_action = _count_consecutive_ticks(
        session,
        statuses={AutonomousRuntimeTickStatus.SKIPPED},
        reason_codes={'no_action', 'watch_only'},
    )
    consecutive_blocked = _count_consecutive_ticks(
        session,
        statuses={AutonomousRuntimeTickStatus.BLOCKED, AutonomousRuntimeTickStatus.FAILED},
    )

    signal_pressure_state = _infer_signal_pressure(
        active_cooldowns=active_cooldown_count,
        recent_dispatch_count=recent_dispatch_count,
        consecutive_no_action=consecutive_no_action,
        recent_loss_count=recent_loss_count,
    )

    reason_codes: list[str] = []
    timing_status = AutonomousTimingStatus.WAIT_SHORT
    decision_type = AutonomousTimingDecisionType.WAIT_SHORT
    next_due_at = now + timedelta(seconds=profile.base_interval_seconds)

    soonest_cooldown = active_cooldowns.first()
    if soonest_cooldown:
        reason_codes.extend(['active_cooldown', *(soonest_cooldown.reason_codes or [])])
        next_due_at = max(soonest_cooldown.expires_at, now + timedelta(seconds=profile.cooldown_extension_seconds))
        timing_status = AutonomousTimingStatus.WAIT_LONG
        decision_type = AutonomousTimingDecisionType.WAIT_LONG

    if recent_dispatch_count > 0 and timing_status != AutonomousTimingStatus.STOP_RECOMMENDED:
        reason_codes.append('recent_dispatch_detected')
        next_due_at = max(next_due_at, now + timedelta(seconds=profile.reduced_interval_seconds + profile.cooldown_extension_seconds))

    if recent_loss_count > 0:
        reason_codes.append('recent_loss_detected')
        timing_status = AutonomousTimingStatus.MONITOR_ONLY_WINDOW
        decision_type = AutonomousTimingDecisionType.MONITOR_ONLY_NEXT
        next_due_at = max(next_due_at, now + timedelta(seconds=profile.monitor_only_interval_seconds))

    if consecutive_no_action >= profile.max_quiet_ticks_before_wait_long:
        reason_codes.append('quiet_market_window')
        timing_status = AutonomousTimingStatus.WAIT_LONG
        decision_type = AutonomousTimingDecisionType.WAIT_LONG
        next_due_at = max(next_due_at, now + timedelta(seconds=profile.monitor_only_interval_seconds))

    if profile.enable_auto_pause_for_quiet_markets and consecutive_no_action >= profile.max_no_action_ticks_before_pause:
        reason_codes.append('auto_pause_quiet_market')
        timing_status = AutonomousTimingStatus.PAUSE_RECOMMENDED
        decision_type = AutonomousTimingDecisionType.PAUSE_SESSION

    if profile.enable_auto_stop_for_persistent_blocks and consecutive_blocked >= profile.max_consecutive_blocked_ticks_before_stop:
        reason_codes.append('persistent_blocks_stop')
        timing_status = AutonomousTimingStatus.STOP_RECOMMENDED
        decision_type = AutonomousTimingDecisionType.STOP_SESSION

    if not active_cooldown_count and consecutive_no_action == 0 and consecutive_blocked == 0 and recent_loss_count == 0 and recent_dispatch_count == 0:
        timing_status = AutonomousTimingStatus.DUE_NOW
        decision_type = AutonomousTimingDecisionType.RUN_NOW
        reason_codes.append('healthy_due_now')
        next_due_at = now

    timing_enforcement = get_module_enforcement_state(module_name='timing_policy')
    impact_status = (timing_enforcement.get('impact') or {}).get('impact_status')
    if impact_status == 'REDUCED':
        reason_codes.append('global_mode_enforcement_reduce_cadence')
        if decision_type == AutonomousTimingDecisionType.RUN_NOW:
            decision_type = AutonomousTimingDecisionType.WAIT_SHORT
            timing_status = AutonomousTimingStatus.WAIT_SHORT
        next_due_at = max(next_due_at, now + timedelta(seconds=max(profile.reduced_interval_seconds, profile.base_interval_seconds)))
    elif impact_status == 'THROTTLED':
        reason_codes.append('global_mode_enforcement_throttle_cadence')
        decision_type = AutonomousTimingDecisionType.WAIT_LONG
        timing_status = AutonomousTimingStatus.WAIT_LONG
        next_due_at = max(next_due_at, now + timedelta(seconds=max(profile.monitor_only_interval_seconds, profile.base_interval_seconds)))
    elif impact_status == 'MONITOR_ONLY':
        reason_codes.append('global_mode_enforcement_monitor_only_cadence')
        decision_type = AutonomousTimingDecisionType.MONITOR_ONLY_NEXT
        timing_status = AutonomousTimingStatus.MONITOR_ONLY_WINDOW
        next_due_at = max(next_due_at, now + timedelta(seconds=profile.monitor_only_interval_seconds))
    elif impact_status == 'BLOCKED':
        reason_codes.append('global_mode_enforcement_block_timing')
        decision_type = AutonomousTimingDecisionType.STOP_SESSION
        timing_status = AutonomousTimingStatus.STOP_RECOMMENDED
        next_due_at = max(next_due_at, now + timedelta(seconds=profile.monitor_only_interval_seconds))

    snapshot = AutonomousSessionTimingSnapshot.objects.create(
        linked_session=session,
        linked_schedule_profile=profile,
        last_tick_at=last_tick_at,
        next_due_at=next_due_at,
        active_cooldown_count=active_cooldown_count,
        consecutive_no_action_ticks=consecutive_no_action,
        consecutive_blocked_ticks=consecutive_blocked,
        recent_dispatch_count=recent_dispatch_count,
        recent_loss_count=recent_loss_count,
        signal_pressure_state=signal_pressure_state,
        timing_status=timing_status,
        timing_summary=f'Timing status={timing_status} with next_due_at={next_due_at.isoformat() if next_due_at else "n/a"}.',
        reason_codes=list(dict.fromkeys(reason_codes)),
        metadata={'latest_tick_id': latest_tick.id if latest_tick else None},
    )

    decision = AutonomousTimingDecision.objects.create(
        linked_session=session,
        linked_timing_snapshot=snapshot,
        decision_type=decision_type,
        decision_status=AutonomousTimingDecisionStatus.PROPOSED,
        next_due_at=next_due_at,
        decision_summary=f'Decision={decision_type} based on {timing_status}.',
        reason_codes=snapshot.reason_codes,
        metadata={'cadence_mode_hint': AutonomousCadenceMode.WAIT_SHORT},
    )

    return TimingReviewResult(snapshot=snapshot, decision=decision)


def map_timing_decision_to_heartbeat(decision: AutonomousTimingDecision) -> tuple[str, bool, str]:
    if decision.decision_type == AutonomousTimingDecisionType.RUN_NOW:
        return AutonomousHeartbeatDecisionType.RUN_DUE_TICK, True, 'Timing policy marked this session due now.'
    if decision.decision_type == AutonomousTimingDecisionType.WAIT_SHORT:
        return AutonomousHeartbeatDecisionType.WAIT_FOR_NEXT_WINDOW, False, 'Timing policy requires a short wait window.'
    if decision.decision_type in {AutonomousTimingDecisionType.WAIT_LONG, AutonomousTimingDecisionType.MONITOR_ONLY_NEXT}:
        return AutonomousHeartbeatDecisionType.SKIP_FOR_COOLDOWN, False, 'Timing policy requires long wait / monitor-only window.'
    if decision.decision_type == AutonomousTimingDecisionType.PAUSE_SESSION:
        return AutonomousHeartbeatDecisionType.PAUSE_SESSION, False, 'Timing policy recommends auto-pause for quiet conditions.'
    return AutonomousHeartbeatDecisionType.STOP_SESSION, False, 'Timing policy recommends auto-stop for persistent blocks.'

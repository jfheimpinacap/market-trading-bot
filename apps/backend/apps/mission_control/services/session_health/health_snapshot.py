from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.utils import timezone

from apps.incident_commander.models import IncidentRecord, IncidentSeverity, IncidentStatus
from apps.mission_control.models import (
    AutonomousCooldownState,
    AutonomousCooldownStatus,
    AutonomousHeartbeatDecision,
    AutonomousIncidentPressureState,
    AutonomousRunnerState,
    AutonomousRuntimeSession,
    AutonomousRuntimeSessionStatus,
    AutonomousRuntimeTickStatus,
    AutonomousSessionHealthRun,
    AutonomousSessionHealthSnapshot,
    AutonomousSessionHealthStatus,
    AutonomousSessionTimingSnapshot,
)
from apps.runtime_governor.services import get_runtime_state
from apps.safety_guard.services import get_safety_status


@dataclass
class HealthSnapshotResult:
    snapshot: AutonomousSessionHealthSnapshot
    hard_block: bool


def _count_consecutive_ticks(session: AutonomousRuntimeSession, *, statuses: set[str], reason_codes: set[str] | None = None) -> int:
    ticks = session.ticks.order_by('-tick_index', '-id')[:25]
    count = 0
    for tick in ticks:
        tick_reasons = set(tick.reason_codes or [])
        if tick.tick_status in statuses or (reason_codes and tick_reasons.intersection(reason_codes)):
            count += 1
            continue
        break
    return count


def _incident_pressure_state(*, session: AutonomousRuntimeSession) -> tuple[str, list[str], dict]:
    lookback = timezone.now() - timedelta(hours=24)
    open_statuses = [IncidentStatus.OPEN, IncidentStatus.ESCALATED, IncidentStatus.DEGRADED, IncidentStatus.MITIGATING]
    related_open = IncidentRecord.objects.filter(
        source_app='mission_control',
        related_object_type='autonomous_runtime_session',
        related_object_id=str(session.id),
        status__in=open_statuses,
        last_seen_at__gte=lookback,
    )
    global_high = IncidentRecord.objects.filter(
        status__in=open_statuses,
        severity__in=[IncidentSeverity.HIGH, IncidentSeverity.CRITICAL],
        last_seen_at__gte=lookback,
    )
    reason_codes: list[str] = []
    state = AutonomousIncidentPressureState.NONE
    if global_high.exists() or related_open.filter(severity=IncidentSeverity.CRITICAL).exists():
        state = AutonomousIncidentPressureState.HIGH
        reason_codes.append('incident_pressure_high')
    elif related_open.exists() or IncidentRecord.objects.filter(status__in=open_statuses, last_seen_at__gte=lookback).exists():
        state = AutonomousIncidentPressureState.CAUTION
        reason_codes.append('incident_pressure_caution')

    metadata = {
        'related_open_incidents': related_open.count(),
        'global_high_incidents': global_high.count(),
    }
    return state, reason_codes, metadata


def build_health_snapshot(*, session: AutonomousRuntimeSession, health_run: AutonomousSessionHealthRun | None = None) -> HealthSnapshotResult:
    now = timezone.now()
    latest_tick = session.ticks.order_by('-tick_index', '-id').first()
    latest_heartbeat = AutonomousHeartbeatDecision.objects.filter(linked_session=session).order_by('-created_at', '-id').first()
    latest_timing_snapshot = AutonomousSessionTimingSnapshot.objects.filter(linked_session=session).order_by('-created_at', '-id').first()
    runner_state = AutonomousRunnerState.objects.filter(runner_name='mission_control_autonomous_heartbeat').first()

    recent_ticks = list(session.ticks.order_by('-created_at', '-id')[:12])
    recent_dispatch_count = sum(1 for tick in recent_ticks if tick.tick_status == AutonomousRuntimeTickStatus.COMPLETED)
    recent_outcome_close_count = sum(1 for tick in recent_ticks if 'outcome_closed' in (tick.reason_codes or []))
    recent_loss_count = sum(1 for tick in recent_ticks if 'loss_detected' in (tick.reason_codes or []))

    consecutive_failed_ticks = _count_consecutive_ticks(session, statuses={AutonomousRuntimeTickStatus.FAILED})
    consecutive_blocked_ticks = _count_consecutive_ticks(session, statuses={AutonomousRuntimeTickStatus.BLOCKED})
    consecutive_no_progress_ticks = _count_consecutive_ticks(
        session,
        statuses={AutonomousRuntimeTickStatus.SKIPPED},
        reason_codes={'no_action', 'watch_only'},
    )

    has_active_cooldown = AutonomousCooldownState.objects.filter(
        linked_session=session,
        cooldown_status=AutonomousCooldownStatus.ACTIVE,
        expires_at__gt=now,
    ).exists()

    safety = get_safety_status()
    runtime_state = get_runtime_state()
    hard_block = bool(safety.get('kill_switch_enabled') or safety.get('hard_stop_active') or runtime_state.current_mode == 'HALTED')

    runner_session_mismatch = False
    if runner_state:
        runner_running = runner_state.runner_status == 'RUNNING'
        session_active = session.session_status == AutonomousRuntimeSessionStatus.RUNNING
        runner_session_mismatch = runner_running != session_active

    incident_pressure_state, incident_codes, incident_metadata = _incident_pressure_state(session=session)

    reason_codes: list[str] = []
    if consecutive_failed_ticks >= 2:
        reason_codes.append('repeated_failed_ticks')
    if consecutive_blocked_ticks >= 2:
        reason_codes.append('repeated_blocked_ticks')
    if consecutive_no_progress_ticks >= 4:
        reason_codes.append('stale_no_progress')
    if runner_session_mismatch:
        reason_codes.append('runner_session_mismatch')
    if has_active_cooldown:
        reason_codes.append('active_cooldown')
    if session.session_status == AutonomousRuntimeSessionStatus.PAUSED:
        reason_codes.append('session_paused')
    if hard_block:
        reason_codes.append('safety_or_runtime_hard_block')
    reason_codes.extend(incident_codes)

    health_status = AutonomousSessionHealthStatus.HEALTHY
    if hard_block or consecutive_blocked_ticks >= 3:
        health_status = AutonomousSessionHealthStatus.BLOCKED
    elif consecutive_failed_ticks >= 2 or runner_session_mismatch:
        health_status = AutonomousSessionHealthStatus.DEGRADED
    elif consecutive_no_progress_ticks >= 5:
        health_status = AutonomousSessionHealthStatus.STALLED
    elif has_active_cooldown or incident_pressure_state != AutonomousIncidentPressureState.NONE or session.session_status == AutonomousRuntimeSessionStatus.PAUSED:
        health_status = AutonomousSessionHealthStatus.CAUTION

    if health_status == AutonomousSessionHealthStatus.HEALTHY and session.session_status == AutonomousRuntimeSessionStatus.RUNNING and recent_dispatch_count == 0:
        health_status = AutonomousSessionHealthStatus.CAUTION
        reason_codes.append('quiet_without_progress')

    summary = (
        f'health={health_status} failed={consecutive_failed_ticks} blocked={consecutive_blocked_ticks} '
        f'no_progress={consecutive_no_progress_ticks} mismatch={runner_session_mismatch} '
        f'incident_pressure={incident_pressure_state}'
    )

    snapshot = AutonomousSessionHealthSnapshot.objects.create(
        linked_health_run=health_run,
        linked_session=session,
        linked_runner_state=runner_state,
        linked_latest_tick=latest_tick,
        linked_latest_heartbeat_decision=latest_heartbeat,
        linked_latest_timing_snapshot=latest_timing_snapshot,
        session_health_status=health_status,
        consecutive_failed_ticks=consecutive_failed_ticks,
        consecutive_blocked_ticks=consecutive_blocked_ticks,
        consecutive_no_progress_ticks=consecutive_no_progress_ticks,
        has_active_cooldown=has_active_cooldown,
        runner_session_mismatch=runner_session_mismatch,
        recent_dispatch_count=recent_dispatch_count,
        recent_outcome_close_count=recent_outcome_close_count,
        recent_loss_count=recent_loss_count,
        incident_pressure_state=incident_pressure_state,
        health_summary=summary,
        reason_codes=list(dict.fromkeys(reason_codes)),
        metadata={
            'runtime_mode': runtime_state.current_mode,
            'session_status': session.session_status,
            'hard_block': hard_block,
            **incident_metadata,
        },
    )
    return HealthSnapshotResult(snapshot=snapshot, hard_block=hard_block)

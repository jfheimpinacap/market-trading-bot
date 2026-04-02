from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from apps.mission_control.models import (
    AutonomousCadenceDecision,
    AutonomousCadenceMode,
    AutonomousCooldownState,
    AutonomousCooldownStatus,
    AutonomousCooldownType,
    AutonomousRuntimeSession,
    AutonomousRuntimeTick,
    AutonomousSignalPressureState,
)
from apps.runtime_governor.services import get_capabilities_for_current_mode
from apps.safety_guard.services import get_safety_status


def _portfolio_posture() -> str:
    try:
        from apps.portfolio_governor.services import get_latest_summary

        return str((get_latest_summary() or {}).get('posture') or 'normal').lower()
    except Exception:
        return 'unknown'


def decide_next_cadence(*, session: AutonomousRuntimeSession, previous_tick: AutonomousRuntimeTick | None = None) -> AutonomousCadenceDecision:
    safety = get_safety_status()
    caps = get_capabilities_for_current_mode()
    portfolio_posture = _portfolio_posture()
    reason_codes: list[str] = []
    cadence_mode = AutonomousCadenceMode.RUN_NOW
    signal_pressure = AutonomousSignalPressureState.NORMAL

    if safety.get('kill_switch_enabled') or safety.get('hard_stop_active'):
        cadence_mode = AutonomousCadenceMode.STOP_SESSION
        reason_codes.append('safety_hard_block')
    elif not bool(caps.get('allow_signal_generation', False) and caps.get('allow_proposals', False)):
        cadence_mode = AutonomousCadenceMode.PAUSE_SESSION
        reason_codes.append('runtime_capability_block')
    elif portfolio_posture in {'constrained', 'caution'}:
        cadence_mode = AutonomousCadenceMode.MONITOR_ONLY_NEXT
        reason_codes.append('portfolio_pressure')
    elif previous_tick and previous_tick.tick_status in {'SKIPPED', 'BLOCKED'}:
        cadence_mode = AutonomousCadenceMode.WAIT_LONG
        signal_pressure = AutonomousSignalPressureState.LOW
        reason_codes.append('cooldown_after_skip_or_block')

    if previous_tick and (previous_tick.linked_cycle_outcome and previous_tick.linked_cycle_outcome.dispatch_count == 0):
        signal_pressure = AutonomousSignalPressureState.QUIET
        if cadence_mode == AutonomousCadenceMode.RUN_NOW:
            cadence_mode = AutonomousCadenceMode.WAIT_SHORT
            reason_codes.append('quiet_window')

    decision = AutonomousCadenceDecision.objects.create(
        linked_session=session,
        linked_previous_tick=previous_tick,
        cadence_mode=cadence_mode,
        cadence_reason_codes=reason_codes,
        portfolio_posture=portfolio_posture,
        runtime_posture='restricted' if not caps.get('allow_auto_execution', False) else 'normal',
        safety_posture='blocked' if safety.get('kill_switch_enabled') or safety.get('hard_stop_active') else 'normal',
        signal_pressure_state=signal_pressure,
        decision_summary=f'Cadence={cadence_mode} for session {session.id}.',
        metadata={'allow_auto_execution': bool(caps.get('allow_auto_execution', False))},
    )

    if cadence_mode == AutonomousCadenceMode.WAIT_SHORT:
        _start_cooldown(session=session, cooldown_type=AutonomousCooldownType.QUIET_MARKET_COOLDOWN, minutes=5, reason_codes=reason_codes)
    elif cadence_mode == AutonomousCadenceMode.WAIT_LONG:
        _start_cooldown(session=session, cooldown_type=AutonomousCooldownType.RUNTIME_CAUTION_COOLDOWN, minutes=15, reason_codes=reason_codes)
    elif cadence_mode == AutonomousCadenceMode.MONITOR_ONLY_NEXT:
        _start_cooldown(session=session, cooldown_type=AutonomousCooldownType.PORTFOLIO_PRESSURE_COOLDOWN, minutes=10, reason_codes=reason_codes)

    return decision


def _start_cooldown(*, session: AutonomousRuntimeSession, cooldown_type: str, minutes: int, reason_codes: list[str]) -> AutonomousCooldownState:
    return AutonomousCooldownState.objects.create(
        linked_session=session,
        cooldown_type=cooldown_type,
        cooldown_status=AutonomousCooldownStatus.ACTIVE,
        started_at=timezone.now(),
        expires_at=timezone.now() + timedelta(minutes=minutes),
        cooldown_summary=f'{cooldown_type} active for {minutes} minutes.',
        reason_codes=reason_codes,
    )

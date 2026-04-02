from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from apps.incident_commander.models import IncidentRecord, IncidentSeverity, IncidentStatus
from apps.mission_control.models import (
    AutonomousCapacityStatus,
    AutonomousGlobalCapacitySnapshot,
    AutonomousGlobalRuntimePosture,
    AutonomousGlobalSafetyPosture,
    AutonomousIncidentPressureState,
    AutonomousOpenPositionPressureState,
    AutonomousRuntimeSession,
    AutonomousRuntimeSessionStatus,
    AutonomousSessionAdmissionRun,
)
from apps.portfolio_governor.models import PortfolioThrottleDecision
from apps.runtime_governor.mode_enforcement.services.enforcement import get_module_enforcement_state
from apps.runtime_governor.services import get_runtime_state
from apps.safety_guard.services import get_safety_status


def build_global_capacity_snapshot(*, admission_run: AutonomousSessionAdmissionRun | None = None) -> AutonomousGlobalCapacitySnapshot:
    runtime_state = get_runtime_state()
    safety = get_safety_status()
    latest_portfolio = PortfolioThrottleDecision.objects.order_by('-created_at_decision', '-id').first()

    running = AutonomousRuntimeSession.objects.filter(session_status=AutonomousRuntimeSessionStatus.RUNNING).count()
    paused = AutonomousRuntimeSession.objects.filter(session_status=AutonomousRuntimeSessionStatus.PAUSED).count()
    degraded = AutonomousRuntimeSession.objects.filter(session_status=AutonomousRuntimeSessionStatus.DEGRADED).count()
    blocked = AutonomousRuntimeSession.objects.filter(session_status=AutonomousRuntimeSessionStatus.BLOCKED).count()

    recent = timezone.now() - timedelta(hours=8)
    active_dispatch_load = sum(s.dispatch_count for s in AutonomousRuntimeSession.objects.filter(updated_at__gte=recent).order_by('-updated_at')[:60])

    portfolio_state = AutonomousOpenPositionPressureState.NORMAL
    if latest_portfolio:
        mapping = {
            'NORMAL': AutonomousOpenPositionPressureState.NORMAL,
            'CAUTION': AutonomousOpenPositionPressureState.CAUTION,
            'THROTTLED': AutonomousOpenPositionPressureState.THROTTLED,
            'BLOCK_NEW_ENTRIES': AutonomousOpenPositionPressureState.BLOCK_NEW_ACTIVITY,
            'FORCE_REDUCE': AutonomousOpenPositionPressureState.BLOCK_NEW_ACTIVITY,
        }
        portfolio_state = mapping.get(latest_portfolio.state, AutonomousOpenPositionPressureState.CAUTION)

    runtime_posture = AutonomousGlobalRuntimePosture.NORMAL
    if runtime_state.status in {'DEGRADED', 'PAUSED'}:
        runtime_posture = AutonomousGlobalRuntimePosture.CAUTION
    elif runtime_state.status == 'STOPPED':
        runtime_posture = AutonomousGlobalRuntimePosture.BLOCKED

    safety_posture = AutonomousGlobalSafetyPosture.NORMAL
    if safety.get('kill_switch_enabled') or safety.get('hard_stop_active'):
        safety_posture = AutonomousGlobalSafetyPosture.HARD_BLOCK
    elif safety.get('status') in {'WARNING', 'COOLDOWN', 'PAUSED'}:
        safety_posture = AutonomousGlobalSafetyPosture.CAUTION

    open_incidents = IncidentRecord.objects.filter(
        status__in=[IncidentStatus.OPEN, IncidentStatus.ESCALATED, IncidentStatus.DEGRADED, IncidentStatus.MITIGATING],
        last_seen_at__gte=timezone.now() - timedelta(hours=24),
    )
    incident_pressure = AutonomousIncidentPressureState.NONE
    if open_incidents.filter(severity__in=[IncidentSeverity.HIGH, IncidentSeverity.CRITICAL]).exists():
        incident_pressure = AutonomousIncidentPressureState.HIGH
    elif open_incidents.exists():
        incident_pressure = AutonomousIncidentPressureState.CAUTION

    max_active_sessions = 3
    if portfolio_state == AutonomousOpenPositionPressureState.CAUTION:
        max_active_sessions = 2
    if portfolio_state in {AutonomousOpenPositionPressureState.THROTTLED, AutonomousOpenPositionPressureState.BLOCK_NEW_ACTIVITY}:
        max_active_sessions = 1
    if runtime_posture == AutonomousGlobalRuntimePosture.CAUTION:
        max_active_sessions = min(max_active_sessions, 2)
    if runtime_posture == AutonomousGlobalRuntimePosture.BLOCKED:
        max_active_sessions = 0
    if safety_posture == AutonomousGlobalSafetyPosture.CAUTION:
        max_active_sessions = min(max_active_sessions, 1)
    if safety_posture == AutonomousGlobalSafetyPosture.HARD_BLOCK:
        max_active_sessions = 0

    admission_enforcement = get_module_enforcement_state(module_name='session_admission')
    admission_impact = (admission_enforcement.get('impact') or {}).get('impact_status')
    if admission_impact == 'REDUCED':
        max_active_sessions = max(1, max_active_sessions - 1)
        reason_codes = ['global_mode_enforcement_reduce_admission']
    elif admission_impact == 'THROTTLED':
        max_active_sessions = min(max_active_sessions, 1)
        reason_codes = ['global_mode_enforcement_throttle_admission']
    elif admission_impact in {'MONITOR_ONLY', 'BLOCKED'}:
        max_active_sessions = 0
        reason_codes = ['global_mode_enforcement_block_new_admission']
    else:
        reason_codes: list[str] = []

    if max_active_sessions == 0:
        capacity_status = AutonomousCapacityStatus.BLOCKED
        reason_codes.append('global_hard_block')
    elif portfolio_state in {AutonomousOpenPositionPressureState.THROTTLED, AutonomousOpenPositionPressureState.BLOCK_NEW_ACTIVITY} or incident_pressure == AutonomousIncidentPressureState.HIGH:
        capacity_status = AutonomousCapacityStatus.THROTTLED
        reason_codes.append('portfolio_or_incident_throttle')
    elif running >= max_active_sessions:
        capacity_status = AutonomousCapacityStatus.LIMITED
        reason_codes.append('at_or_above_active_limit')
    else:
        capacity_status = AutonomousCapacityStatus.AVAILABLE

    if active_dispatch_load >= 25:
        reason_codes.append('high_dispatch_load')

    summary = f'capacity={capacity_status} max_active={max_active_sessions} running={running} portfolio={portfolio_state} runtime={runtime_posture} safety={safety_posture}'

    return AutonomousGlobalCapacitySnapshot.objects.create(
        linked_admission_run=admission_run,
        max_active_sessions=max_active_sessions,
        current_running_sessions=running,
        current_paused_sessions=paused,
        current_degraded_sessions=degraded,
        current_blocked_sessions=blocked,
        active_dispatch_load=active_dispatch_load,
        open_position_pressure_state=portfolio_state,
        runtime_posture=runtime_posture,
        safety_posture=safety_posture,
        incident_pressure_state=incident_pressure,
        capacity_status=capacity_status,
        snapshot_summary=summary,
        reason_codes=reason_codes,
        metadata={
            'runtime_mode': runtime_state.current_mode,
            'runtime_status': runtime_state.status,
            'safety_status': safety.get('status'),
            'portfolio_state': latest_portfolio.state if latest_portfolio else 'UNAVAILABLE',
        },
    )

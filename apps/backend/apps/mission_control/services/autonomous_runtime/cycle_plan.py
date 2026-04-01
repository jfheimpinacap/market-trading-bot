from __future__ import annotations

from dataclasses import dataclass

from apps.mission_control.models import (
    AutonomousMissionCyclePlan,
    AutonomousMissionCyclePlanStatus,
    AutonomousMissionRuntimeRun,
)
from apps.runtime_governor.services import get_capabilities_for_current_mode, get_runtime_state
from apps.safety_guard.services import get_safety_status


@dataclass
class RuntimeContext:
    runtime_mode: str
    portfolio_posture: str
    safety_posture: str
    degraded_mode_state: str
    reason_codes: list[str]


def _portfolio_posture() -> str:
    try:
        from apps.portfolio_governor.services import get_latest_summary

        summary = get_latest_summary()
        return str(summary.get('posture') or 'normal').lower()
    except Exception:
        return 'unknown'


def _degraded_mode_state() -> str:
    try:
        from apps.incident_commander.services import get_current_degraded_mode_state

        return str(get_current_degraded_mode_state().state or 'normal').lower()
    except Exception:
        return 'normal'


def build_cycle_plan(*, runtime_run: AutonomousMissionRuntimeRun) -> AutonomousMissionCyclePlan:
    runtime_state = get_runtime_state()
    safety = get_safety_status()
    caps = get_capabilities_for_current_mode()
    portfolio_posture = _portfolio_posture()
    degraded_state = _degraded_mode_state()
    reason_codes: list[str] = []

    step_flags = {
        'scan_review': True,
        'pursuit_review': True,
        'prediction_intake': True,
        'risk_intake': True,
        'execution_intake': bool(caps.get('allow_auto_execution', False)),
        'position_watch': True,
        'outcome_handoff': True,
        'feedback_reuse': True,
    }
    status = AutonomousMissionCyclePlanStatus.READY
    summary = 'Full governed cycle planned.'

    if safety.get('kill_switch_enabled') or safety.get('hard_stop_active'):
        status = AutonomousMissionCyclePlanStatus.BLOCKED
        step_flags['execution_intake'] = False
        reason_codes.extend(['safety_blocked'])
        summary = 'Cycle blocked by safety hard stop/kill switch.'
    elif not bool(caps.get('allow_signal_generation', False) and caps.get('allow_proposals', False)):
        status = AutonomousMissionCyclePlanStatus.BLOCKED
        step_flags['execution_intake'] = False
        reason_codes.append('runtime_blocks_upstream')
        summary = 'Cycle blocked by runtime capability restrictions.'
    elif portfolio_posture in {'caution', 'constrained'} or degraded_state in {'degraded', 'caution'}:
        status = AutonomousMissionCyclePlanStatus.REDUCED
        step_flags['execution_intake'] = False
        reason_codes.append('reduced_for_posture')
        summary = 'Reduced cycle: monitor/watch/outcome/learning without execution dispatch.'

    context = RuntimeContext(
        runtime_mode=runtime_state.current_mode,
        portfolio_posture=portfolio_posture,
        safety_posture='blocked' if safety.get('kill_switch_enabled') or safety.get('hard_stop_active') else 'normal',
        degraded_mode_state=degraded_state,
        reason_codes=reason_codes,
    )

    return AutonomousMissionCyclePlan.objects.create(
        linked_runtime_run=runtime_run,
        planned_step_flags=step_flags,
        plan_status=status,
        runtime_mode=context.runtime_mode,
        portfolio_posture=context.portfolio_posture,
        safety_posture=context.safety_posture,
        degraded_mode_state=context.degraded_mode_state,
        plan_summary=summary,
        reason_codes=context.reason_codes,
        metadata={'runtime_status': runtime_state.status},
    )

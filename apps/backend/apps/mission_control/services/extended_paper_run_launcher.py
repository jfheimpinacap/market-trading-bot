from __future__ import annotations

from copy import deepcopy
from threading import Lock
from typing import Any

from apps.mission_control.models import AutonomousRuntimeSession
from apps.mission_control.services.extended_paper_run_gate import (
    GATE_ALLOW,
    GATE_ALLOW_WITH_CAUTION,
    GATE_BLOCK,
    build_extended_paper_run_gate,
)
from apps.mission_control.services.live_paper_bootstrap import (
    BOOTSTRAP_ACTION_BLOCKED,
    BOOTSTRAP_ACTION_CREATED_AND_STARTED,
    BOOTSTRAP_ACTION_FAILED,
    BOOTSTRAP_ACTION_REUSED_EXISTING_SESSION,
    BOOTSTRAP_ACTION_STARTED_EXISTING_SAFE_SESSION,
    MARKET_DATA_MODE_REAL_READ_ONLY,
    PAPER_EXECUTION_MODE_PAPER_ONLY,
    PRESET_NAME,
    bootstrap_live_read_only_paper_session,
    get_live_paper_bootstrap_status,
)

LAUNCH_STATUS_STARTED = 'STARTED'
LAUNCH_STATUS_REUSED_RUNNING_SESSION = 'REUSED_RUNNING_SESSION'
LAUNCH_STATUS_REUSED_PAUSED_SESSION = 'REUSED_PAUSED_SESSION'
LAUNCH_STATUS_BLOCKED = 'BLOCKED'
LAUNCH_STATUS_FAILED = 'FAILED'

_REASON_GATE_BLOCKED = 'GATE_BLOCKED'
_REASON_LAUNCH_STARTED = 'EXTENDED_RUN_STARTED'
_REASON_REUSED_RUNNING = 'REUSED_RUNNING_SESSION'
_REASON_REUSED_PAUSED = 'REUSED_PAUSED_SESSION'
_REASON_BOOTSTRAP_BLOCKED = 'BOOTSTRAP_BLOCKED'
_REASON_BOOTSTRAP_FAILED = 'BOOTSTRAP_FAILED'
_REASON_INVALID_BOUNDARY_MARKET_DATA = 'INVALID_MARKET_DATA_MODE'
_REASON_INVALID_BOUNDARY_EXECUTION = 'INVALID_EXECUTION_MODE'
_REASON_INVALID_BOUNDARY_LIVE_EXECUTION = 'INVALID_LIVE_EXECUTION_FLAG'

_last_launch_lock = Lock()
_last_launch_result: dict[str, Any] | None = None


def _store_last_launch(payload: dict[str, Any]) -> None:
    global _last_launch_result
    with _last_launch_lock:
        _last_launch_result = deepcopy(payload)


def _get_last_launch() -> dict[str, Any] | None:
    with _last_launch_lock:
        return deepcopy(_last_launch_result)


def _build_caution_mode(gate_status: str, *, for_failed_or_blocked: bool = False) -> bool | None:
    if gate_status == GATE_ALLOW_WITH_CAUTION:
        return True
    if gate_status == GATE_ALLOW:
        return False
    return None if for_failed_or_blocked else False


def _build_launch_status_from_bootstrap_action(action: str) -> str:
    if action == BOOTSTRAP_ACTION_CREATED_AND_STARTED:
        return LAUNCH_STATUS_STARTED
    if action == BOOTSTRAP_ACTION_REUSED_EXISTING_SESSION:
        return LAUNCH_STATUS_REUSED_RUNNING_SESSION
    if action == BOOTSTRAP_ACTION_STARTED_EXISTING_SAFE_SESSION:
        return LAUNCH_STATUS_REUSED_PAUSED_SESSION
    if action == BOOTSTRAP_ACTION_BLOCKED:
        return LAUNCH_STATUS_FAILED
    if action == BOOTSTRAP_ACTION_FAILED:
        return LAUNCH_STATUS_FAILED
    return LAUNCH_STATUS_FAILED


def _boundary_reason_codes(*, bootstrap_status: dict[str, Any], session_id: int | None) -> list[str]:
    reasons: list[str] = []
    if bootstrap_status.get('market_data_mode') != MARKET_DATA_MODE_REAL_READ_ONLY:
        reasons.append(_REASON_INVALID_BOUNDARY_MARKET_DATA)
    if bootstrap_status.get('paper_execution_mode') != PAPER_EXECUTION_MODE_PAPER_ONLY:
        reasons.append(_REASON_INVALID_BOUNDARY_EXECUTION)

    if session_id:
        session = AutonomousRuntimeSession.objects.filter(id=session_id).only('metadata').first()
        metadata = (session.metadata or {}) if session else {}
        if metadata.get('live_execution_enabled') is True:
            reasons.append(_REASON_INVALID_BOUNDARY_LIVE_EXECUTION)

    return reasons


def _build_hint(*, launch_status: str, gate_status: str, caution_mode: bool | None, session_active: bool, heartbeat_active: bool) -> str:
    if launch_status == '':
        return 'Start extended run to lock an active launch state'
    if launch_status == LAUNCH_STATUS_BLOCKED:
        return 'Extended run blocked by gate; resolve validation/trial/attention blockers first'
    if launch_status == LAUNCH_STATUS_FAILED:
        return 'Extended run launch failed; inspect bootstrap and runtime guardrails'
    if caution_mode:
        return 'Extended run active in caution mode; monitor first cycles and attention bridge closely'
    if session_active and heartbeat_active:
        return 'Extended run active; keep monitoring heartbeat cadence and paper risk posture'
    if gate_status == GATE_ALLOW:
        return 'Gate allows run, but heartbeat/session are not fully active yet'
    return 'Extended run is warming up; verify session and heartbeat state'


def launch_extended_paper_run(*, preset_name: str | None = None) -> dict[str, Any]:
    target_preset = (preset_name or PRESET_NAME).strip() or PRESET_NAME
    gate = build_extended_paper_run_gate(preset_name=target_preset)
    gate_status = str(gate.get('gate_status') or GATE_BLOCK)

    if gate_status == GATE_BLOCK:
        bootstrap_status = get_live_paper_bootstrap_status(preset_name=target_preset)
        payload = {
            'preset_name': target_preset,
            'launch_status': LAUNCH_STATUS_BLOCKED,
            'gate_status': gate_status,
            'session_active': bool(bootstrap_status.get('session_active')),
            'heartbeat_active': bool(bootstrap_status.get('heartbeat_active')),
            'current_session_status': str(bootstrap_status.get('current_session_status') or 'MISSING'),
            'caution_mode': None,
            'next_action_hint': _build_hint(
                launch_status=LAUNCH_STATUS_BLOCKED,
                gate_status=gate_status,
                caution_mode=None,
                session_active=bool(bootstrap_status.get('session_active')),
                heartbeat_active=bool(bootstrap_status.get('heartbeat_active')),
            ),
            'launch_summary': f"{LAUNCH_STATUS_BLOCKED}: gate={gate_status}; launch not executed.",
            'reason_codes': [_REASON_GATE_BLOCKED, *(gate.get('reason_codes') or [])],
        }
        _store_last_launch(payload)
        return payload

    bootstrap_result = bootstrap_live_read_only_paper_session(
        preset_name=target_preset,
        auto_start_heartbeat=True,
        start_now=True,
    )
    bootstrap_status = get_live_paper_bootstrap_status(preset_name=target_preset)
    launch_status = _build_launch_status_from_bootstrap_action(str(bootstrap_result.get('bootstrap_action') or ''))
    session_id = bootstrap_result.get('session_id')

    boundary_reasons = _boundary_reason_codes(bootstrap_status=bootstrap_status, session_id=session_id)
    if boundary_reasons:
        launch_status = LAUNCH_STATUS_FAILED

    caution_mode = _build_caution_mode(gate_status, for_failed_or_blocked=launch_status in {LAUNCH_STATUS_FAILED, LAUNCH_STATUS_BLOCKED})

    reason_codes = list(gate.get('reason_codes') or [])
    if launch_status == LAUNCH_STATUS_STARTED:
        reason_codes.insert(0, _REASON_LAUNCH_STARTED)
    elif launch_status == LAUNCH_STATUS_REUSED_RUNNING_SESSION:
        reason_codes.insert(0, _REASON_REUSED_RUNNING)
    elif launch_status == LAUNCH_STATUS_REUSED_PAUSED_SESSION:
        reason_codes.insert(0, _REASON_REUSED_PAUSED)
    elif str(bootstrap_result.get('bootstrap_action')) == BOOTSTRAP_ACTION_BLOCKED:
        reason_codes.insert(0, _REASON_BOOTSTRAP_BLOCKED)
    else:
        reason_codes.insert(0, _REASON_BOOTSTRAP_FAILED)

    reason_codes.extend(boundary_reasons)

    payload = {
        'preset_name': target_preset,
        'launch_status': launch_status,
        'gate_status': gate_status,
        'session_active': bool(bootstrap_status.get('session_active')),
        'heartbeat_active': bool(bootstrap_status.get('heartbeat_active')),
        'current_session_status': str(bootstrap_status.get('current_session_status') or 'MISSING'),
        'caution_mode': caution_mode,
        'next_action_hint': _build_hint(
            launch_status=launch_status,
            gate_status=gate_status,
            caution_mode=caution_mode,
            session_active=bool(bootstrap_status.get('session_active')),
            heartbeat_active=bool(bootstrap_status.get('heartbeat_active')),
        ),
        'launch_summary': (
            f"{launch_status}: gate={gate_status}, bootstrap_action={bootstrap_result.get('bootstrap_action')}, "
            f"session_active={bool(bootstrap_status.get('session_active'))}, heartbeat_active={bool(bootstrap_status.get('heartbeat_active'))}."
        ),
        'reason_codes': list(dict.fromkeys(reason_codes)),
    }
    _store_last_launch(payload)
    return payload


def get_extended_paper_run_status(*, preset_name: str | None = None) -> dict[str, Any]:
    target_preset = (preset_name or PRESET_NAME).strip() or PRESET_NAME
    gate = build_extended_paper_run_gate(preset_name=target_preset)
    bootstrap_status = get_live_paper_bootstrap_status(preset_name=target_preset)
    last_launch = _get_last_launch() or {}

    gate_status = str(gate.get('gate_status') or GATE_BLOCK)
    caution_mode = _build_caution_mode(gate_status, for_failed_or_blocked=gate_status == GATE_BLOCK)
    session_active = bool(bootstrap_status.get('session_active'))
    heartbeat_active = bool(bootstrap_status.get('heartbeat_active'))
    launch_status = str(last_launch.get('launch_status') or '')
    launch_exists = bool(launch_status)

    extended_run_active = (
        gate_status in {GATE_ALLOW, GATE_ALLOW_WITH_CAUTION}
        and session_active
        and heartbeat_active
        and launch_status in {
            LAUNCH_STATUS_STARTED,
            LAUNCH_STATUS_REUSED_RUNNING_SESSION,
            LAUNCH_STATUS_REUSED_PAUSED_SESSION,
        }
    )

    if extended_run_active and caution_mode:
        status_summary = 'Extended run active in caution mode with gate warnings acknowledged.'
    elif extended_run_active:
        status_summary = 'Extended run active in normal mode with gate ALLOW.'
    elif launch_status == LAUNCH_STATUS_BLOCKED or gate_status == GATE_BLOCK:
        status_summary = 'Extended run blocked by gate; launch not active.'
    elif launch_status == LAUNCH_STATUS_FAILED:
        status_summary = 'Extended run launch failed; launch not active.'
    else:
        status_summary = 'Extended run not active yet; launch has not started in this process.'

    return {
        'exists': launch_exists,
        'status': 'AVAILABLE' if launch_exists else 'NO_RUN_YET',
        'summary': status_summary,
        'reason_code': 'EXTENDED_RUN_STATUS_AVAILABLE' if launch_exists else 'EXTENDED_RUN_NOT_STARTED',
        'preset_name': target_preset,
        'extended_run_active': extended_run_active,
        'gate_status': gate_status,
        'session_active': session_active,
        'heartbeat_active': heartbeat_active,
        'current_session_status': str(bootstrap_status.get('current_session_status') or 'MISSING'),
        'caution_mode': caution_mode,
        'status_summary': status_summary,
        'next_action_hint': _build_hint(
            launch_status=launch_status,
            gate_status=gate_status,
            caution_mode=caution_mode,
            session_active=session_active,
            heartbeat_active=heartbeat_active,
        ),
    }

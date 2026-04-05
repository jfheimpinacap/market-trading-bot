from __future__ import annotations

from copy import deepcopy
from threading import Lock

from django.utils import timezone

from apps.mission_control.services.live_paper_bootstrap import (
    BOOTSTRAP_ACTION_BLOCKED,
    BOOTSTRAP_ACTION_FAILED,
    PRESET_NAME,
    bootstrap_live_read_only_paper_session,
    get_live_paper_bootstrap_status,
)
from apps.mission_control.services.live_paper_validation import build_live_paper_validation_digest
from apps.mission_control.services.session_heartbeat import build_heartbeat_summary, run_heartbeat_pass

SMOKE_STATUS_PASS = 'PASS'
SMOKE_STATUS_WARN = 'WARN'
SMOKE_STATUS_FAIL = 'FAIL'

_CHECK_PASS = 'PASS'
_CHECK_WARN = 'WARN'
_CHECK_FAIL = 'FAIL'

_BLOCKING_VALIDATION = {'BLOCKED'}
_last_result_lock = Lock()
_last_result: dict | None = None


def _check(*, check_name: str, status: str, summary: str) -> dict[str, str]:
    return {
        'check_name': check_name,
        'status': status,
        'summary': summary,
    }


def _build_hint(*, smoke_test_status: str, validation_after: str, recent_activity_detected: bool, recent_trades_detected: bool) -> str:
    if smoke_test_status == SMOKE_STATUS_PASS:
        return 'Live paper smoke test passed'
    if validation_after == 'BLOCKED':
        return 'Operational attention requires review'
    if validation_after == 'WARNING':
        return 'Review cockpit and let autopilot continue'
    if not recent_activity_detected:
        return 'Wait for another heartbeat pass'
    if not recent_trades_detected:
        return 'Wait for another heartbeat pass'
    return 'Review cockpit and let autopilot continue'


def _compute_smoke_status(
    *,
    bootstrap_action: str,
    session_active_after: bool,
    heartbeat_active_after: bool,
    validation_status_after: str,
    recent_activity_detected: bool,
    paper_snapshot_ready: bool,
) -> str:
    bootstrap_failed = bootstrap_action in {BOOTSTRAP_ACTION_BLOCKED, BOOTSTRAP_ACTION_FAILED}
    session_failed = not session_active_after
    heartbeat_failed = not heartbeat_active_after
    validation_blocked = validation_status_after in _BLOCKING_VALIDATION

    if bootstrap_failed or session_failed or heartbeat_failed or validation_blocked or not paper_snapshot_ready:
        return SMOKE_STATUS_FAIL

    weak_signal = (not recent_activity_detected) or validation_status_after == 'WARNING'
    if weak_signal:
        return SMOKE_STATUS_WARN

    return SMOKE_STATUS_PASS


def _build_summary(*, smoke_test_status: str, validation_before: str, validation_after: str, heartbeat_passes_completed: int) -> str:
    return (
        f'{smoke_test_status}: validation {validation_before} -> {validation_after}; '
        f'heartbeat_passes_completed={heartbeat_passes_completed}.'
    )


def _store_last_result(payload: dict) -> None:
    global _last_result
    with _last_result_lock:
        _last_result = deepcopy(payload)


def get_last_live_paper_smoke_test_result() -> dict | None:
    with _last_result_lock:
        return deepcopy(_last_result)


def run_live_paper_smoke_test(*, preset_name: str | None = None, heartbeat_passes: int = 1) -> dict:
    target_preset = (preset_name or PRESET_NAME).strip() or PRESET_NAME
    requested_passes = max(1, min(int(heartbeat_passes or 1), 2))

    validation_before = build_live_paper_validation_digest(preset_name=target_preset)

    bootstrap_result = bootstrap_live_read_only_paper_session(
        preset_name=target_preset,
        auto_start_heartbeat=True,
        start_now=True,
    )

    completed_passes = 0
    for _ in range(requested_passes):
        run_heartbeat_pass()
        completed_passes += 1

    validation_after = build_live_paper_validation_digest(preset_name=target_preset)
    bootstrap_status = get_live_paper_bootstrap_status(preset_name=target_preset)
    heartbeat_summary = build_heartbeat_summary()

    recent_activity_detected = bool(validation_after.get('recent_activity_present') or heartbeat_summary.get('latest_run'))
    recent_trades_detected = bool(validation_after.get('recent_trades_present'))
    paper_snapshot_ready = bool(validation_after.get('portfolio_snapshot_ready'))

    smoke_test_status = _compute_smoke_status(
        bootstrap_action=str(bootstrap_result.get('bootstrap_action') or ''),
        session_active_after=bool(bootstrap_status.get('session_active')),
        heartbeat_active_after=bool(bootstrap_status.get('heartbeat_active')),
        validation_status_after=str(validation_after.get('validation_status') or ''),
        recent_activity_detected=recent_activity_detected,
        paper_snapshot_ready=paper_snapshot_ready,
    )

    checks = [
        _check(
            check_name='bootstrap',
            status=_CHECK_FAIL if bootstrap_result.get('bootstrap_action') in {BOOTSTRAP_ACTION_BLOCKED, BOOTSTRAP_ACTION_FAILED} else _CHECK_PASS,
            summary=str(bootstrap_result.get('bootstrap_summary') or 'Bootstrap executed.'),
        ),
        _check(
            check_name='heartbeat',
            status=_CHECK_PASS if completed_passes == requested_passes else _CHECK_FAIL,
            summary=f'Heartbeat passes completed={completed_passes} requested={requested_passes}.',
        ),
        _check(
            check_name='validation_before',
            status=_CHECK_FAIL if validation_before.get('validation_status') == 'BLOCKED' else (_CHECK_WARN if validation_before.get('validation_status') == 'WARNING' else _CHECK_PASS),
            summary=str(validation_before.get('validation_summary') or ''),
        ),
        _check(
            check_name='validation_after',
            status=_CHECK_FAIL if validation_after.get('validation_status') == 'BLOCKED' else (_CHECK_WARN if validation_after.get('validation_status') == 'WARNING' else _CHECK_PASS),
            summary=str(validation_after.get('validation_summary') or ''),
        ),
        _check(
            check_name='activity_signal',
            status=_CHECK_PASS if recent_activity_detected else _CHECK_WARN,
            summary='Recent activity evidence detected.' if recent_activity_detected else 'No recent activity evidence yet.',
        ),
        _check(
            check_name='paper_snapshot',
            status=_CHECK_PASS if paper_snapshot_ready else _CHECK_FAIL,
            summary='Paper snapshot with balances is available.' if paper_snapshot_ready else 'Paper snapshot with balances is missing.',
        ),
    ]

    next_action_hint = _build_hint(
        smoke_test_status=smoke_test_status,
        validation_after=str(validation_after.get('validation_status') or ''),
        recent_activity_detected=recent_activity_detected,
        recent_trades_detected=recent_trades_detected,
    )

    response_payload = {
        'preset_name': target_preset,
        'smoke_test_status': smoke_test_status,
        'executed_at': timezone.now(),
        'bootstrap_action': bootstrap_result.get('bootstrap_action'),
        'session_active_after': bool(bootstrap_status.get('session_active')),
        'heartbeat_active_after': bool(bootstrap_status.get('heartbeat_active')),
        'validation_status_before': validation_before.get('validation_status'),
        'validation_status_after': validation_after.get('validation_status'),
        'heartbeat_passes_requested': requested_passes,
        'heartbeat_passes_completed': completed_passes,
        'recent_activity_detected': recent_activity_detected,
        'recent_trades_detected': recent_trades_detected,
        'next_action_hint': next_action_hint,
        'smoke_test_summary': _build_summary(
            smoke_test_status=smoke_test_status,
            validation_before=str(validation_before.get('validation_status') or 'UNKNOWN'),
            validation_after=str(validation_after.get('validation_status') or 'UNKNOWN'),
            heartbeat_passes_completed=completed_passes,
        ),
        'checks': checks,
    }

    _store_last_result(response_payload)
    return response_payload

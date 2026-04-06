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
from apps.mission_control.services.live_paper_smoke_test import (
    SMOKE_STATUS_FAIL,
    SMOKE_STATUS_PASS,
    SMOKE_STATUS_WARN,
    get_last_live_paper_smoke_test_result,
    run_live_paper_smoke_test,
)
from apps.mission_control.services.live_paper_validation import build_live_paper_validation_digest

TRIAL_STATUS_PASS = 'PASS'
TRIAL_STATUS_WARN = 'WARN'
TRIAL_STATUS_FAIL = 'FAIL'

_CHECK_PASS = 'PASS'
_CHECK_WARN = 'WARN'
_CHECK_FAIL = 'FAIL'

_last_trial_result_lock = Lock()
_last_trial_result: dict | None = None


def _check(*, check_name: str, status: str, summary: str) -> dict[str, str]:
    return {
        'check_name': check_name,
        'status': status,
        'summary': summary,
    }


def _normalize_validation_status(status_value: str | None) -> str:
    value = (status_value or '').upper().strip()
    if value in {'READY', 'WARNING', 'BLOCKED'}:
        return value
    return 'BLOCKED'


def _compute_trial_status(
    *,
    bootstrap_action: str,
    smoke_test_status: str,
    validation_status_after: str,
    recent_activity_detected: bool,
    recent_trades_detected: bool,
    portfolio_snapshot_ready: bool,
) -> str:
    if (
        bootstrap_action in {BOOTSTRAP_ACTION_BLOCKED, BOOTSTRAP_ACTION_FAILED}
        or smoke_test_status == SMOKE_STATUS_FAIL
        or validation_status_after == 'BLOCKED'
    ):
        return TRIAL_STATUS_FAIL

    if smoke_test_status == SMOKE_STATUS_PASS and validation_status_after == 'READY' and portfolio_snapshot_ready and (
        recent_activity_detected or recent_trades_detected
    ):
        return TRIAL_STATUS_PASS

    return TRIAL_STATUS_WARN


def _build_next_action_hint(*, trial_status: str, validation_status_after: str, smoke_test_status: str, bootstrap_action: str, heartbeat_passes_completed: int) -> str:
    if bootstrap_action in {BOOTSTRAP_ACTION_BLOCKED, BOOTSTRAP_ACTION_FAILED}:
        return 'Bootstrap failed; inspect mission control'
    if trial_status == TRIAL_STATUS_PASS:
        return 'Live paper trial passed'
    if validation_status_after == 'WARNING':
        return 'Review validation warnings'
    if smoke_test_status == SMOKE_STATUS_WARN or heartbeat_passes_completed < 2:
        return 'Wait for another heartbeat pass'
    return 'Let autopilot continue and monitor portfolio'


def _build_trial_summary(*, trial_status: str, smoke_test_status: str, validation_before: str, validation_after: str, heartbeat_passes_completed: int) -> str:
    return (
        f'{trial_status}: smoke={smoke_test_status} validation {validation_before}->{validation_after}; '
        f'heartbeat_passes_completed={heartbeat_passes_completed}.'
    )


def _store_last_trial_result(payload: dict) -> None:
    global _last_trial_result
    with _last_trial_result_lock:
        _last_trial_result = deepcopy(payload)


def get_last_live_paper_trial_run_result() -> dict | None:
    with _last_trial_result_lock:
        return deepcopy(_last_trial_result)


def run_live_paper_trial_run(*, preset_name: str | None = None, heartbeat_passes: int = 1) -> dict:
    target_preset = (preset_name or PRESET_NAME).strip() or PRESET_NAME
    requested_passes = max(1, min(int(heartbeat_passes or 1), 2))

    validation_before = build_live_paper_validation_digest(preset_name=target_preset)

    bootstrap_result = bootstrap_live_read_only_paper_session(
        preset_name=target_preset,
        auto_start_heartbeat=True,
        start_now=True,
    )
    bootstrap_status = get_live_paper_bootstrap_status(preset_name=target_preset)

    smoke_result = run_live_paper_smoke_test(
        preset_name=target_preset,
        heartbeat_passes=requested_passes,
    )
    smoke_status_payload = get_last_live_paper_smoke_test_result() or smoke_result

    validation_after = build_live_paper_validation_digest(preset_name=target_preset)
    validation_status_before = _normalize_validation_status(validation_before.get('validation_status'))
    validation_status_after = _normalize_validation_status(validation_after.get('validation_status'))

    recent_activity_detected = bool(validation_after.get('recent_activity_present'))
    recent_trades_detected = bool(validation_after.get('recent_trades_present'))
    portfolio_snapshot_ready = bool(validation_after.get('portfolio_snapshot_ready'))
    smoke_test_status = str(smoke_status_payload.get('smoke_test_status') or SMOKE_STATUS_FAIL)

    trial_status = _compute_trial_status(
        bootstrap_action=str(bootstrap_result.get('bootstrap_action') or ''),
        smoke_test_status=smoke_test_status,
        validation_status_after=validation_status_after,
        recent_activity_detected=recent_activity_detected,
        recent_trades_detected=recent_trades_detected,
        portfolio_snapshot_ready=portfolio_snapshot_ready,
    )

    checks = [
        _check(
            check_name='bootstrap',
            status=_CHECK_FAIL if bootstrap_result.get('bootstrap_action') in {BOOTSTRAP_ACTION_BLOCKED, BOOTSTRAP_ACTION_FAILED} else _CHECK_PASS,
            summary=str(bootstrap_result.get('bootstrap_summary') or bootstrap_status.get('status_summary') or 'Bootstrap evaluated.'),
        ),
        _check(
            check_name='smoke_test',
            status=_CHECK_FAIL if smoke_test_status == SMOKE_STATUS_FAIL else (_CHECK_WARN if smoke_test_status == SMOKE_STATUS_WARN else _CHECK_PASS),
            summary=str(smoke_status_payload.get('smoke_test_summary') or 'Smoke test executed.'),
        ),
        _check(
            check_name='validation_before',
            status=_CHECK_FAIL if validation_status_before == 'BLOCKED' else (_CHECK_WARN if validation_status_before == 'WARNING' else _CHECK_PASS),
            summary=str(validation_before.get('validation_summary') or ''),
        ),
        _check(
            check_name='validation_after',
            status=_CHECK_FAIL if validation_status_after == 'BLOCKED' else (_CHECK_WARN if validation_status_after == 'WARNING' else _CHECK_PASS),
            summary=str(validation_after.get('validation_summary') or ''),
        ),
        _check(
            check_name='portfolio_snapshot',
            status=_CHECK_PASS if portfolio_snapshot_ready else _CHECK_WARN,
            summary='Portfolio snapshot is ready.' if portfolio_snapshot_ready else 'Portfolio snapshot still warming up.',
        ),
        _check(
            check_name='recent_activity',
            status=_CHECK_PASS if recent_activity_detected else _CHECK_WARN,
            summary='Recent autonomous activity detected.' if recent_activity_detected else 'No recent autonomous activity detected yet.',
        ),
        _check(
            check_name='recent_trades',
            status=_CHECK_PASS if recent_trades_detected else _CHECK_WARN,
            summary='Recent paper trades detected.' if recent_trades_detected else 'No recent paper trades detected yet.',
        ),
    ]

    response_payload = {
        'preset_name': target_preset,
        'trial_status': trial_status,
        'executed_at': timezone.now(),
        'bootstrap_action': bootstrap_result.get('bootstrap_action'),
        'smoke_test_status': smoke_test_status,
        'validation_status_before': validation_status_before,
        'validation_status_after': validation_status_after,
        'heartbeat_passes_requested': requested_passes,
        'heartbeat_passes_completed': int(smoke_status_payload.get('heartbeat_passes_completed') or 0),
        'recent_activity_detected': recent_activity_detected,
        'recent_trades_detected': recent_trades_detected,
        'portfolio_snapshot_ready': portfolio_snapshot_ready,
        'next_action_hint': _build_next_action_hint(
            trial_status=trial_status,
            validation_status_after=validation_status_after,
            smoke_test_status=smoke_test_status,
            bootstrap_action=str(bootstrap_result.get('bootstrap_action') or ''),
            heartbeat_passes_completed=int(smoke_status_payload.get('heartbeat_passes_completed') or 0),
        ),
        'trial_summary': _build_trial_summary(
            trial_status=trial_status,
            smoke_test_status=smoke_test_status,
            validation_before=validation_status_before,
            validation_after=validation_status_after,
            heartbeat_passes_completed=int(smoke_status_payload.get('heartbeat_passes_completed') or 0),
        ),
        'checks': checks,
    }

    _store_last_trial_result(response_payload)
    return response_payload

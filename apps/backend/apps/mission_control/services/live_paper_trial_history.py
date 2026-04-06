from __future__ import annotations

from collections import deque
from copy import deepcopy
from threading import Lock

from django.utils import timezone

_HISTORY_CAPACITY = 20
_DEFAULT_LIMIT = 5
_ALLOWED_STATUSES = {'PASS', 'WARN', 'FAIL'}

_history_lock = Lock()
_history_buffer: deque[dict] = deque(maxlen=_HISTORY_CAPACITY)

_HISTORY_FIELDS = (
    'created_at',
    'preset_name',
    'trial_status',
    'bootstrap_action',
    'smoke_test_status',
    'validation_status_after',
    'heartbeat_passes_completed',
    'next_action_hint',
    'trial_summary',
    'recent_activity_detected',
    'recent_trades_detected',
    'portfolio_snapshot_ready',
)


def _normalize_status(status: str | None) -> str | None:
    normalized = (status or '').upper().strip()
    if normalized in _ALLOWED_STATUSES:
        return normalized
    return None


def _build_history_item(result: dict) -> dict:
    payload = {
        'created_at': result.get('executed_at') or timezone.now(),
        'preset_name': result.get('preset_name'),
        'trial_status': _normalize_status(result.get('trial_status')) or 'FAIL',
        'bootstrap_action': result.get('bootstrap_action'),
        'smoke_test_status': result.get('smoke_test_status'),
        'validation_status_after': result.get('validation_status_after'),
        'heartbeat_passes_completed': int(result.get('heartbeat_passes_completed') or 0),
        'next_action_hint': result.get('next_action_hint') or '',
        'trial_summary': result.get('trial_summary') or '',
    }
    for optional_field in ('recent_activity_detected', 'recent_trades_detected', 'portfolio_snapshot_ready'):
        if optional_field in result:
            payload[optional_field] = bool(result.get(optional_field))
    return payload


def _build_history_summary(*, items: list[dict], latest_trial_status: str | None) -> str:
    if not items:
        return 'No live paper trial history recorded yet'

    recent_window_size = min(2, len(items))
    recent_window = items[:recent_window_size]
    recent_statuses = [item.get('trial_status') for item in recent_window]

    if recent_statuses and all(status == 'WARN' for status in recent_statuses):
        return f'Recent trial history shows warnings in the last {recent_window_size} runs'

    if recent_statuses and any(status == 'FAIL' for status in recent_statuses):
        return f'Recent trial history shows failures in the last {recent_window_size} runs'

    return f'{len(items)} recent trial runs recorded; latest status {latest_trial_status}'


def record_live_paper_trial_result(result: dict) -> None:
    history_item = _build_history_item(result)
    with _history_lock:
        _history_buffer.appendleft(deepcopy(history_item))


def list_live_paper_trial_history(*, limit: int = _DEFAULT_LIMIT, status: str | None = None) -> dict:
    safe_limit = max(1, min(int(limit or _DEFAULT_LIMIT), _HISTORY_CAPACITY))
    status_filter = _normalize_status(status)

    with _history_lock:
        items = deepcopy(list(_history_buffer))

    if status_filter:
        items = [item for item in items if item.get('trial_status') == status_filter]

    trimmed_items = items[:safe_limit]
    latest_trial_status = trimmed_items[0].get('trial_status') if trimmed_items else None

    return {
        'count': len(trimmed_items),
        'latest_trial_status': latest_trial_status,
        'history_summary': _build_history_summary(items=trimmed_items, latest_trial_status=latest_trial_status),
        'items': [
            {field: item.get(field) for field in _HISTORY_FIELDS if field in item}
            for item in trimmed_items
        ],
    }


def _clear_live_paper_trial_history_for_tests() -> None:
    with _history_lock:
        _history_buffer.clear()

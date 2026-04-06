from __future__ import annotations

from collections import Counter

from apps.mission_control.services.live_paper_trial_history import list_live_paper_trial_history

TREND_IMPROVING = 'IMPROVING'
TREND_STABLE = 'STABLE'
TREND_DEGRADING = 'DEGRADING'
TREND_INSUFFICIENT_DATA = 'INSUFFICIENT_DATA'

READINESS_READY = 'READY_FOR_EXTENDED_RUN'
READINESS_REVIEW = 'NEEDS_REVIEW'
READINESS_NOT_READY = 'NOT_READY'

_STATUS_SCORE = {
    'PASS': 3,
    'WARN': 2,
    'FAIL': 1,
}

_DEFAULT_LIMIT = 5


def _status_score(status: str | None) -> int:
    return _STATUS_SCORE.get((status or '').upper(), 0)


def _count_statuses(statuses: list[str]) -> dict[str, int]:
    counts = Counter(statuses)
    return {
        'pass_count': int(counts.get('PASS', 0)),
        'warn_count': int(counts.get('WARN', 0)),
        'fail_count': int(counts.get('FAIL', 0)),
    }


def _split_windows(statuses: list[str]) -> tuple[list[str], list[str]]:
    pivot = max(1, len(statuses) // 2)
    return statuses[:pivot], statuses[pivot:]


def _compute_trend_status(statuses: list[str]) -> str:
    if len(statuses) < 2:
        return TREND_INSUFFICIENT_DATA

    latest_status = statuses[0]
    previous_status = statuses[1]
    latest_score = _status_score(latest_status)
    previous_score = _status_score(previous_status)

    if latest_score > previous_score:
        return TREND_IMPROVING
    if latest_score < previous_score:
        return TREND_DEGRADING

    if all(status == 'PASS' for status in statuses):
        return TREND_STABLE

    if latest_status == 'FAIL' and any(status in {'PASS', 'WARN'} for status in statuses[1:]):
        return TREND_DEGRADING

    recent_window, older_window = _split_windows(statuses)
    recent_bad = sum(1 for status in recent_window if status in {'WARN', 'FAIL'})
    older_bad = sum(1 for status in older_window if status in {'WARN', 'FAIL'})
    recent_pass = sum(1 for status in recent_window if status == 'PASS')
    older_pass = sum(1 for status in older_window if status == 'PASS')

    if recent_bad > older_bad:
        return TREND_DEGRADING
    if recent_pass > older_pass and older_bad > 0:
        return TREND_IMPROVING

    return TREND_STABLE


def _compute_readiness_status(*, trend_status: str, latest_trial_status: str | None, counts: dict[str, int]) -> str:
    if latest_trial_status == 'FAIL' or trend_status == TREND_DEGRADING:
        return READINESS_NOT_READY

    if latest_trial_status == 'PASS' and trend_status in {TREND_STABLE, TREND_IMPROVING}:
        return READINESS_READY

    warn_count = counts.get('warn_count', 0)
    pass_count = counts.get('pass_count', 0)
    if warn_count >= max(1, pass_count):
        return READINESS_REVIEW

    return READINESS_REVIEW


def _build_trend_summary(*, trend_status: str, sample_size: int, counts: dict[str, int], latest_trial_status: str | None) -> str:
    if trend_status == TREND_INSUFFICIENT_DATA:
        return f'Insufficient data: {sample_size} recent trial run available.'

    return (
        f'{trend_status}: latest={latest_trial_status}, '
        f'PASS={counts["pass_count"]}, WARN={counts["warn_count"]}, FAIL={counts["fail_count"]} '
        f'across {sample_size} runs.'
    )


def _build_next_action_hint(*, readiness_status: str, trend_status: str, latest_trial_status: str | None) -> str:
    if readiness_status == READINESS_READY:
        return 'Proceed to a longer paper session'
    if readiness_status == READINESS_NOT_READY:
        return 'Do not start extended paper run yet'
    if trend_status == TREND_INSUFFICIENT_DATA:
        return 'Run one more trial before extended run'
    if latest_trial_status == 'WARN' or trend_status == TREND_DEGRADING:
        return 'Review recent warnings before proceeding'
    return 'Run one more trial before extended run'


def build_live_paper_trial_trend_digest(*, limit: int = _DEFAULT_LIMIT, preset: str | None = None) -> dict:
    history_payload = list_live_paper_trial_history(limit=limit)
    history_items = history_payload.get('items', [])

    if preset:
        preset_normalized = preset.strip()
        history_items = [item for item in history_items if item.get('preset_name') == preset_normalized]

    statuses = [str(item.get('trial_status') or '').upper() for item in history_items]
    statuses = [status for status in statuses if status in _STATUS_SCORE]

    sample_size = len(statuses)
    latest_item = history_items[0] if history_items else {}
    latest_trial_status = statuses[0] if statuses else None
    latest_validation_status = latest_item.get('validation_status_after') if latest_item else None

    counts = _count_statuses(statuses)
    trend_status = _compute_trend_status(statuses)
    readiness_status = _compute_readiness_status(
        trend_status=trend_status,
        latest_trial_status=latest_trial_status,
        counts=counts,
    )

    return {
        'sample_size': sample_size,
        'latest_trial_status': latest_trial_status,
        'latest_validation_status': latest_validation_status,
        'trend_status': trend_status,
        'readiness_status': readiness_status,
        'trend_summary': _build_trend_summary(
            trend_status=trend_status,
            sample_size=sample_size,
            counts=counts,
            latest_trial_status=latest_trial_status,
        ),
        'next_action_hint': _build_next_action_hint(
            readiness_status=readiness_status,
            trend_status=trend_status,
            latest_trial_status=latest_trial_status,
        ),
        'counts': counts,
        'recent_statuses': statuses,
    }

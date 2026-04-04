from __future__ import annotations

from typing import Any

from apps.runtime_governor.services.tuning_alerts import (
    ALERT_STATUS_MINOR_CHANGE,
    ALERT_STATUS_PROFILE_SHIFT,
    ALERT_STATUS_REVIEW_NOW,
    ALERT_STATUS_STABLE,
    build_tuning_change_alerts,
)

ALERT_PRIORITY = {
    ALERT_STATUS_REVIEW_NOW: 4,
    ALERT_STATUS_PROFILE_SHIFT: 3,
    ALERT_STATUS_MINOR_CHANGE: 2,
    ALERT_STATUS_STABLE: 1,
}


def _status_counts(alerts: list[dict[str, Any]]) -> dict[str, int]:
    return {
        ALERT_STATUS_STABLE: sum(1 for row in alerts if row.get('alert_status') == ALERT_STATUS_STABLE),
        ALERT_STATUS_MINOR_CHANGE: sum(1 for row in alerts if row.get('alert_status') == ALERT_STATUS_MINOR_CHANGE),
        ALERT_STATUS_PROFILE_SHIFT: sum(1 for row in alerts if row.get('alert_status') == ALERT_STATUS_PROFILE_SHIFT),
        ALERT_STATUS_REVIEW_NOW: sum(1 for row in alerts if row.get('alert_status') == ALERT_STATUS_REVIEW_NOW),
    }


def _order_alerts(alerts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        alerts,
        key=lambda row: (
            ALERT_PRIORITY.get(str(row.get('alert_status')), 0),
            row.get('created_at') or '',
            row.get('source_scope') or '',
        ),
        reverse=True,
    )


def _build_summary(*, ordered_alerts: list[dict[str, Any]], counts: dict[str, int]) -> str:
    total = len(ordered_alerts)
    if total == 0:
        return 'No tuning change alerts available yet.'

    if counts[ALERT_STATUS_REVIEW_NOW] == 0 and counts[ALERT_STATUS_PROFILE_SHIFT] == 0 and counts[ALERT_STATUS_MINOR_CHANGE] == 0:
        return f'All {total} scope(s) are STABLE. No immediate tuning review is needed.'

    top_scopes = ', '.join(row['source_scope'] for row in ordered_alerts[:3])
    return (
        f"Review first: {top_scopes}. "
        f"Priority counts — REVIEW_NOW: {counts[ALERT_STATUS_REVIEW_NOW]}, "
        f"PROFILE_SHIFT: {counts[ALERT_STATUS_PROFILE_SHIFT]}, "
        f"MINOR_CHANGE: {counts[ALERT_STATUS_MINOR_CHANGE]}, STABLE: {counts[ALERT_STATUS_STABLE]}."
    )


def build_tuning_alert_summary(*, source_scope: str | None = None) -> dict[str, Any]:
    alerts = build_tuning_change_alerts(source_scope=source_scope)
    ordered_alerts = _order_alerts(alerts)
    counts = _status_counts(ordered_alerts)
    changed_alerts = [row for row in ordered_alerts if row.get('alert_status') != ALERT_STATUS_STABLE]
    most_recent_changed_alert = max(
        changed_alerts,
        key=lambda row: (row.get('created_at') or '', row.get('source_scope') or ''),
        default=None,
    )

    return {
        'total_scope_count': len(ordered_alerts),
        'stable_count': counts[ALERT_STATUS_STABLE],
        'minor_change_count': counts[ALERT_STATUS_MINOR_CHANGE],
        'profile_shift_count': counts[ALERT_STATUS_PROFILE_SHIFT],
        'review_now_count': counts[ALERT_STATUS_REVIEW_NOW],
        'highest_priority_scope': ordered_alerts[0]['source_scope'] if ordered_alerts else None,
        'most_recent_changed_scope': most_recent_changed_alert['source_scope'] if most_recent_changed_alert else None,
        'ordered_scopes': [
            {
                'source_scope': row['source_scope'],
                'alert_status': row['alert_status'],
                'latest_snapshot_id': row['latest_snapshot_id'],
                'created_at': row.get('created_at'),
                'alert_summary': row.get('alert_summary', ''),
            }
            for row in ordered_alerts
        ],
        'summary': _build_summary(ordered_alerts=ordered_alerts, counts=counts),
    }

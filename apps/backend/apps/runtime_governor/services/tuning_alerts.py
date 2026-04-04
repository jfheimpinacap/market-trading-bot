from __future__ import annotations

from typing import Any

from apps.runtime_governor.models import RuntimeTuningContextDriftStatus, RuntimeTuningContextSnapshot
from apps.runtime_governor.services.tuning_diff import build_tuning_context_diffs
from apps.runtime_governor.services.tuning_digest import build_tuning_scope_digest

ALERT_STATUS_STABLE = 'STABLE'
ALERT_STATUS_MINOR_CHANGE = 'MINOR_CHANGE'
ALERT_STATUS_PROFILE_SHIFT = 'PROFILE_SHIFT'
ALERT_STATUS_REVIEW_NOW = 'REVIEW_NOW'

DRIFT_TO_ALERT_STATUS = {
    RuntimeTuningContextDriftStatus.NO_CHANGE: ALERT_STATUS_STABLE,
    RuntimeTuningContextDriftStatus.MINOR_CONTEXT_CHANGE: ALERT_STATUS_MINOR_CHANGE,
    RuntimeTuningContextDriftStatus.PROFILE_CHANGE: ALERT_STATUS_PROFILE_SHIFT,
    RuntimeTuningContextDriftStatus.INITIAL: ALERT_STATUS_MINOR_CHANGE,
}

REVIEW_NOW_RELEVANT_PREFIXES = (
    'effective_values.',
    'guardrails.',
)
REVIEW_NOW_MIN_RELEVANT_CHANGES = 3
REVIEW_NOW_RECENT_WINDOW = 3


def _is_relevant_change(field_name: str) -> bool:
    return any(field_name.startswith(prefix) for prefix in REVIEW_NOW_RELEVANT_PREFIXES)


def _has_recent_profile_shift(*, source_scope: str, exclude_snapshot_id: int) -> bool:
    recent_statuses = list(
        RuntimeTuningContextSnapshot.objects.filter(source_scope=source_scope)
        .exclude(id=exclude_snapshot_id)
        .order_by('-created_at_snapshot', '-id')
        .values_list('drift_status', flat=True)[:REVIEW_NOW_RECENT_WINDOW]
    )
    return RuntimeTuningContextDriftStatus.PROFILE_CHANGE in recent_statuses


def _build_alert_status(*, latest_drift_status: str, relevant_change_count: int, has_recent_profile_shift: bool) -> str:
    base_status = DRIFT_TO_ALERT_STATUS.get(latest_drift_status, ALERT_STATUS_MINOR_CHANGE)
    if relevant_change_count >= REVIEW_NOW_MIN_RELEVANT_CHANGES:
        return ALERT_STATUS_REVIEW_NOW
    if has_recent_profile_shift:
        return ALERT_STATUS_REVIEW_NOW
    return base_status


def _build_alert_summary(
    *,
    source_scope: str,
    latest_snapshot_id: int,
    latest_drift_status: str,
    alert_status: str,
    relevant_change_count: int,
    has_recent_profile_shift: bool,
) -> str:
    clauses = [
        f'scope {source_scope}',
        f'snapshot #{latest_snapshot_id}',
        f'drift {latest_drift_status}',
        f'alert {alert_status}',
    ]
    if relevant_change_count:
        clauses.append(f'{relevant_change_count} relevant field change(s)')
    if has_recent_profile_shift:
        clauses.append('recent profile shift observed')
    return '; '.join(clauses) + '.'


def build_tuning_change_alerts(*, source_scope: str | None = None) -> list[dict[str, Any]]:
    digest_rows = build_tuning_scope_digest(source_scope=source_scope)
    if not digest_rows:
        return []

    latest_snapshot_ids = [row['latest_snapshot_id'] for row in digest_rows]
    latest_snapshots = list(RuntimeTuningContextSnapshot.objects.filter(id__in=latest_snapshot_ids))
    diff_by_snapshot_id = {
        row['current_snapshot_id']: row for row in build_tuning_context_diffs(snapshots=latest_snapshots)
    }

    alerts: list[dict[str, Any]] = []
    for digest in digest_rows:
        diff_row = diff_by_snapshot_id.get(digest['latest_snapshot_id'], {})
        changed_fields = diff_row.get('changed_fields', {}) or {}
        relevant_change_count = sum(1 for field_name in changed_fields if _is_relevant_change(field_name))
        recent_profile_shift = _has_recent_profile_shift(
            source_scope=digest['source_scope'],
            exclude_snapshot_id=digest['latest_snapshot_id'],
        )
        alert_status = _build_alert_status(
            latest_drift_status=digest['latest_drift_status'],
            relevant_change_count=relevant_change_count,
            has_recent_profile_shift=recent_profile_shift,
        )
        alerts.append(
            {
                'source_scope': digest['source_scope'],
                'latest_snapshot_id': digest['latest_snapshot_id'],
                'tuning_profile_name': digest['tuning_profile_name'],
                'tuning_profile_fingerprint': digest['tuning_profile_fingerprint'],
                'latest_drift_status': digest['latest_drift_status'],
                'alert_status': alert_status,
                'alert_summary': _build_alert_summary(
                    source_scope=digest['source_scope'],
                    latest_snapshot_id=digest['latest_snapshot_id'],
                    latest_drift_status=digest['latest_drift_status'],
                    alert_status=alert_status,
                    relevant_change_count=relevant_change_count,
                    has_recent_profile_shift=recent_profile_shift,
                ),
                'created_at': digest['latest_snapshot_created_at'],
            }
        )
    return alerts

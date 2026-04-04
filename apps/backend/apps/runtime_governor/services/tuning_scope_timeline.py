from __future__ import annotations

from typing import Any

from apps.runtime_governor.models import RuntimeTuningContextDriftStatus, RuntimeTuningContextSnapshot
from apps.runtime_governor.services.tuning_alerts import (
    ALERT_STATUS_MINOR_CHANGE,
    ALERT_STATUS_PROFILE_SHIFT,
    ALERT_STATUS_REVIEW_NOW,
    ALERT_STATUS_STABLE,
    DRIFT_TO_ALERT_STATUS,
)
from apps.runtime_governor.services.tuning_correlation import build_tuning_run_correlations
from apps.runtime_governor.services.tuning_diff import build_tuning_context_diffs
from apps.runtime_governor.services.tuning_links import build_latest_diff_links

DEFAULT_TIMELINE_LIMIT = 5
MAX_TIMELINE_SCAN = 20
RECENT_FLAG_WINDOW = 5

TIMELINE_LABEL_INITIAL = 'INITIAL_SNAPSHOT'
TIMELINE_LABEL_STABLE = 'STABLE_BASELINE'
TIMELINE_LABEL_MINOR = 'MINOR_CONTEXT_UPDATE'
TIMELINE_LABEL_PROFILE_SHIFT = 'PROFILE_SHIFT'
TIMELINE_LABEL_REVIEW_NOW = 'REVIEW_NOW'

TIMELINE_REASON_PROFILE_SHIFT = 'PROFILE_SHIFT'
TIMELINE_REASON_REVIEW_NOW = 'REVIEW_NOW'
TIMELINE_REASON_STABLE = 'STABLE'
TIMELINE_REASON_MINOR_CHANGE = 'MINOR_CHANGE'
TIMELINE_REASON_DIFF_FIELDS_CHANGED = 'DIFF_FIELDS_CHANGED'
TIMELINE_REASON_GUARDRAIL_CHANGED = 'GUARDRAIL_CHANGED'
TIMELINE_REASON_NO_COMPARABLE_DIFF = 'NO_COMPARABLE_DIFF'
TIMELINE_REASON_INITIAL = 'INITIAL_SNAPSHOT'


def _build_alert_status(*, drift_status: str, changed_field_count: int, changed_guardrail_count: int) -> str:
    if drift_status == RuntimeTuningContextDriftStatus.PROFILE_CHANGE:
        return ALERT_STATUS_PROFILE_SHIFT
    if changed_field_count >= 3 or changed_guardrail_count >= 2:
        return ALERT_STATUS_REVIEW_NOW
    return DRIFT_TO_ALERT_STATUS.get(drift_status, ALERT_STATUS_MINOR_CHANGE)


def _build_timeline_label(*, drift_status: str, has_comparable_diff: bool, alert_status: str, changed_field_count: int) -> str:
    if drift_status == RuntimeTuningContextDriftStatus.INITIAL or not has_comparable_diff:
        return TIMELINE_LABEL_INITIAL
    if alert_status == ALERT_STATUS_REVIEW_NOW:
        return TIMELINE_LABEL_REVIEW_NOW
    if drift_status == RuntimeTuningContextDriftStatus.PROFILE_CHANGE:
        return TIMELINE_LABEL_PROFILE_SHIFT
    if alert_status == ALERT_STATUS_STABLE or changed_field_count == 0:
        return TIMELINE_LABEL_STABLE
    return TIMELINE_LABEL_MINOR


def _build_reason_codes(
    *,
    drift_status: str,
    alert_status: str,
    has_comparable_diff: bool,
    changed_field_count: int,
    changed_guardrail_count: int,
) -> list[str]:
    reason_codes: list[str] = []
    if drift_status == RuntimeTuningContextDriftStatus.INITIAL:
        reason_codes.append(TIMELINE_REASON_INITIAL)
    if drift_status == RuntimeTuningContextDriftStatus.PROFILE_CHANGE:
        reason_codes.append(TIMELINE_REASON_PROFILE_SHIFT)
    if alert_status == ALERT_STATUS_REVIEW_NOW:
        reason_codes.append(TIMELINE_REASON_REVIEW_NOW)
    if alert_status == ALERT_STATUS_STABLE:
        reason_codes.append(TIMELINE_REASON_STABLE)
    if alert_status == ALERT_STATUS_MINOR_CHANGE:
        reason_codes.append(TIMELINE_REASON_MINOR_CHANGE)
    if has_comparable_diff and changed_field_count > 0:
        reason_codes.append(TIMELINE_REASON_DIFF_FIELDS_CHANGED)
    if has_comparable_diff and changed_guardrail_count > 0:
        reason_codes.append(TIMELINE_REASON_GUARDRAIL_CHANGED)
    if not has_comparable_diff:
        reason_codes.append(TIMELINE_REASON_NO_COMPARABLE_DIFF)
    return reason_codes[:4]


def _build_timeline_summary(*, entries: list[dict[str, Any]]) -> str:
    if not entries:
        return 'No snapshots available for this scope.'
    if len(entries) == 1:
        return 'Insufficient history: only 1 snapshot available for this scope.'

    recent_entries = entries[:RECENT_FLAG_WINDOW]
    profile_shift_count = sum(1 for entry in recent_entries if entry['timeline_label'] == TIMELINE_LABEL_PROFILE_SHIFT)
    review_now_count = sum(1 for entry in recent_entries if entry['timeline_label'] == TIMELINE_LABEL_REVIEW_NOW)
    stable_count = sum(1 for entry in recent_entries if entry['alert_status'] == ALERT_STATUS_STABLE)
    minor_change_count = sum(1 for entry in recent_entries if entry['timeline_label'] == TIMELINE_LABEL_MINOR)

    if review_now_count > 0:
        return f'Recent timeline includes {review_now_count} REVIEW_NOW event(s).'
    if profile_shift_count > 0:
        return f'Recent timeline includes {profile_shift_count} PROFILE_SHIFT event(s).'
    if stable_count == len(recent_entries):
        return 'Recent timeline is stable with no significant changes.'
    if minor_change_count >= 2:
        return f'Recent timeline shows repeated minor updates ({minor_change_count} entries).'
    return 'Recent timeline shows mixed but low-severity tuning changes.'


def _with_non_stable_filter(*, entries: list[dict[str, Any]], include_stable: bool) -> list[dict[str, Any]]:
    if include_stable:
        return entries
    if not entries:
        return []
    latest_entry = entries[0]
    filtered = [entry for entry in entries if entry['alert_status'] != ALERT_STATUS_STABLE]
    if not filtered:
        return [latest_entry]
    if filtered[0]['snapshot_id'] != latest_entry['snapshot_id']:
        filtered.insert(0, latest_entry)
    return filtered


def build_tuning_scope_timeline(*, source_scope: str, limit: int = DEFAULT_TIMELINE_LIMIT, include_stable: bool = True) -> dict[str, Any] | None:
    resolved_limit = limit if limit > 0 else DEFAULT_TIMELINE_LIMIT
    snapshots = list(
        RuntimeTuningContextSnapshot.objects.filter(source_scope=source_scope).order_by('-created_at_snapshot', '-id')[:MAX_TIMELINE_SCAN]
    )
    if not snapshots:
        return None

    diff_rows = build_tuning_context_diffs(snapshots=snapshots)
    diff_by_snapshot_id = {row['current_snapshot_id']: row for row in diff_rows}
    links_by_scope = build_latest_diff_links(latest_snapshots=[snapshots[0]])
    correlations = build_tuning_run_correlations(snapshots=snapshots)
    correlation_by_snapshot_id = {row['tuning_snapshot_id']: row for row in correlations}

    entries: list[dict[str, Any]] = []
    for snapshot in snapshots:
        diff_row = diff_by_snapshot_id.get(snapshot.id, {})
        has_comparable_diff = diff_row.get('previous_snapshot_id') is not None
        changed_fields = diff_row.get('changed_fields', {}) if has_comparable_diff else {}
        changed_field_count = len(changed_fields)
        changed_guardrail_count = sum(1 for field_name in changed_fields if field_name.startswith('guardrails.'))

        alert_status = _build_alert_status(
            drift_status=snapshot.drift_status,
            changed_field_count=changed_field_count,
            changed_guardrail_count=changed_guardrail_count,
        )
        timeline_label = _build_timeline_label(
            drift_status=snapshot.drift_status,
            has_comparable_diff=has_comparable_diff,
            alert_status=alert_status,
            changed_field_count=changed_field_count,
        )
        correlation_row = correlation_by_snapshot_id.get(snapshot.id, {})

        entries.append(
            {
                'snapshot_id': snapshot.id,
                'created_at': snapshot.created_at_snapshot,
                'drift_status': snapshot.drift_status,
                'alert_status': alert_status,
                'profile_name': snapshot.tuning_profile_name,
                'profile_fingerprint': snapshot.tuning_profile_fingerprint,
                'diff_summary': diff_row.get('diff_summary') if has_comparable_diff else 'No comparable previous snapshot.',
                'has_comparable_diff': has_comparable_diff,
                'changed_field_count': changed_field_count,
                'changed_guardrail_count': changed_guardrail_count,
                'correlated_run_id': correlation_row.get('source_run_id') if correlation_row.get('run_created_at') else None,
                'correlated_run_timestamp': correlation_row.get('run_created_at') if correlation_row.get('run_created_at') else None,
                'timeline_reason_codes': _build_reason_codes(
                    drift_status=snapshot.drift_status,
                    alert_status=alert_status,
                    has_comparable_diff=has_comparable_diff,
                    changed_field_count=changed_field_count,
                    changed_guardrail_count=changed_guardrail_count,
                ),
                'timeline_label': timeline_label,
            }
        )

    filtered_entries = _with_non_stable_filter(entries=entries, include_stable=include_stable)[:resolved_limit]

    latest_snapshot = snapshots[0]
    latest_link = links_by_scope.get(source_scope, {})
    recent_for_flags = filtered_entries[:RECENT_FLAG_WINDOW] if filtered_entries else []

    return {
        'source_scope': source_scope,
        'entry_count': len(filtered_entries),
        'latest_snapshot_id': latest_snapshot.id,
        'latest_snapshot_created_at': latest_snapshot.created_at_snapshot,
        'timeline_summary': _build_timeline_summary(entries=filtered_entries),
        'is_recently_stable': bool(recent_for_flags) and all(entry['alert_status'] == ALERT_STATUS_STABLE for entry in recent_for_flags),
        'has_recent_profile_shift': any(entry['timeline_label'] == TIMELINE_LABEL_PROFILE_SHIFT for entry in recent_for_flags),
        'has_recent_review_now': any(entry['alert_status'] == ALERT_STATUS_REVIEW_NOW for entry in recent_for_flags),
        'latest_diff_snapshot_id': latest_link.get('latest_diff_snapshot_id'),
        'entries': filtered_entries,
    }

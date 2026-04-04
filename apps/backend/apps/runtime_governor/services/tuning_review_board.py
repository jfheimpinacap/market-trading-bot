from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from apps.runtime_governor.models import RuntimeTuningContextSnapshot
from apps.runtime_governor.services.tuning_alerts import (
    ALERT_STATUS_MINOR_CHANGE,
    ALERT_STATUS_PROFILE_SHIFT,
    ALERT_STATUS_REVIEW_NOW,
    ALERT_STATUS_STABLE,
    build_tuning_change_alerts,
)
from apps.runtime_governor.services.tuning_correlation import build_tuning_run_correlations
from apps.runtime_governor.services.tuning_diff import build_tuning_context_diffs
from apps.runtime_governor.services.tuning_digest import build_tuning_scope_digest

ATTENTION_PRIORITY_ORDER = {
    ALERT_STATUS_REVIEW_NOW: 4,
    ALERT_STATUS_PROFILE_SHIFT: 3,
    ALERT_STATUS_MINOR_CHANGE: 2,
    ALERT_STATUS_STABLE: 1,
}

REASON_PROFILE_SHIFT = 'PROFILE_SHIFT'
REASON_GUARDRAIL_CHANGE = 'GUARDRAIL_CHANGE'
REASON_EFFECTIVE_VALUE_CHANGE = 'EFFECTIVE_VALUE_CHANGE'
REASON_MULTI_FIELD_CHANGE = 'MULTI_FIELD_CHANGE'
REASON_NO_COMPARABLE_DIFF = 'NO_COMPARABLE_DIFF'
REASON_NO_CORRELATED_RUN = 'NO_CORRELATED_RUN'
REASON_STABLE_NO_ACTION = 'STABLE_NO_ACTION'

ACTION_OPEN_LATEST_DIFF = 'OPEN_LATEST_DIFF'
ACTION_CHECK_CORRELATED_RUN = 'CHECK_CORRELATED_RUN'
ACTION_MONITOR_ONLY = 'MONITOR_ONLY'
ACTION_NO_ACTION_REQUIRED = 'NO_ACTION_REQUIRED'


@dataclass(frozen=True)
class _ReviewComputation:
    changed_field_count: int
    changed_guardrail_count: int
    review_reason_codes: list[str]
    recommended_next_action: str
    board_summary: str


def _count_guardrail_changes(changed_fields: dict[str, Any]) -> int:
    return sum(1 for field_name in changed_fields if str(field_name).startswith('guardrails.'))


def _build_review_reason_codes(
    *,
    alert_status: str,
    drift_status: str,
    changed_fields: dict[str, Any],
    has_comparable_diff: bool,
    correlated_run_id: int | None,
) -> list[str]:
    reason_codes: list[str] = []

    if alert_status == ALERT_STATUS_PROFILE_SHIFT or drift_status == 'PROFILE_CHANGE':
        reason_codes.append(REASON_PROFILE_SHIFT)

    guardrail_change_count = _count_guardrail_changes(changed_fields)
    if guardrail_change_count > 0:
        reason_codes.append(REASON_GUARDRAIL_CHANGE)

    if any(str(field_name).startswith('effective_values.') for field_name in changed_fields):
        reason_codes.append(REASON_EFFECTIVE_VALUE_CHANGE)

    if len(changed_fields) > 1:
        reason_codes.append(REASON_MULTI_FIELD_CHANGE)

    if not has_comparable_diff:
        reason_codes.append(REASON_NO_COMPARABLE_DIFF)

    if correlated_run_id is None and alert_status != ALERT_STATUS_STABLE:
        reason_codes.append(REASON_NO_CORRELATED_RUN)

    if alert_status == ALERT_STATUS_STABLE and not reason_codes:
        reason_codes.append(REASON_STABLE_NO_ACTION)

    return reason_codes


def _build_recommended_next_action(*, alert_status: str, latest_diff_snapshot_id: int | None, correlated_run_id: int | None) -> str:
    if latest_diff_snapshot_id is not None:
        return ACTION_OPEN_LATEST_DIFF
    if correlated_run_id is not None and alert_status != ALERT_STATUS_STABLE:
        return ACTION_CHECK_CORRELATED_RUN
    if alert_status == ALERT_STATUS_STABLE:
        return ACTION_NO_ACTION_REQUIRED
    return ACTION_MONITOR_ONLY


def _build_board_summary(
    *,
    source_scope: str,
    attention_priority: str,
    drift_status: str,
    changed_field_count: int,
    changed_guardrail_count: int,
    recommended_next_action: str,
) -> str:
    return (
        f'{source_scope}: {attention_priority} ({drift_status}); '
        f'{changed_field_count} changed field(s), {changed_guardrail_count} guardrail change(s). '
        f'Next action: {recommended_next_action}.'
    )


def _compute_review(
    *,
    source_scope: str,
    alert_status: str,
    drift_status: str,
    changed_fields: dict[str, Any],
    has_comparable_diff: bool,
    latest_diff_snapshot_id: int | None,
    correlated_run_id: int | None,
) -> _ReviewComputation:
    changed_field_count = len(changed_fields) if has_comparable_diff else 0
    changed_guardrail_count = _count_guardrail_changes(changed_fields) if has_comparable_diff else 0
    review_reason_codes = _build_review_reason_codes(
        alert_status=alert_status,
        drift_status=drift_status,
        changed_fields=changed_fields if has_comparable_diff else {},
        has_comparable_diff=has_comparable_diff,
        correlated_run_id=correlated_run_id,
    )
    recommended_next_action = _build_recommended_next_action(
        alert_status=alert_status,
        latest_diff_snapshot_id=latest_diff_snapshot_id,
        correlated_run_id=correlated_run_id,
    )
    board_summary = _build_board_summary(
        source_scope=source_scope,
        attention_priority=alert_status,
        drift_status=drift_status,
        changed_field_count=changed_field_count,
        changed_guardrail_count=changed_guardrail_count,
        recommended_next_action=recommended_next_action,
    )
    return _ReviewComputation(
        changed_field_count=changed_field_count,
        changed_guardrail_count=changed_guardrail_count,
        review_reason_codes=review_reason_codes,
        recommended_next_action=recommended_next_action,
        board_summary=board_summary,
    )


def _build_base_rows(*, source_scope: str | None = None) -> list[dict[str, Any]]:
    digest_rows = build_tuning_scope_digest(source_scope=source_scope)
    if not digest_rows:
        return []

    alerts_by_scope = {row['source_scope']: row for row in build_tuning_change_alerts(source_scope=source_scope)}
    latest_snapshots = list(RuntimeTuningContextSnapshot.objects.filter(id__in=[row['latest_snapshot_id'] for row in digest_rows]))
    diffs_by_snapshot_id = {row['current_snapshot_id']: row for row in build_tuning_context_diffs(snapshots=latest_snapshots)}
    correlations_by_scope = {row['source_scope']: row for row in build_tuning_run_correlations(snapshots=latest_snapshots)}

    rows: list[dict[str, Any]] = []
    for digest in digest_rows:
        scope = digest['source_scope']
        alert = alerts_by_scope.get(scope, {})
        diff = diffs_by_snapshot_id.get(digest['latest_snapshot_id'], {})
        correlation = correlations_by_scope.get(scope, {})

        comparable_diff = diff.get('previous_snapshot_id') is not None and digest.get('latest_diff_snapshot_id') is not None
        changed_fields = diff.get('changed_fields', {}) or {}
        correlated_run_timestamp = correlation.get('run_created_at')
        correlated_run_id = correlation.get('source_run_id') if correlated_run_timestamp else None
        review = _compute_review(
            source_scope=scope,
            alert_status=alert.get('alert_status', ALERT_STATUS_MINOR_CHANGE),
            drift_status=digest['latest_drift_status'],
            changed_fields=changed_fields,
            has_comparable_diff=comparable_diff,
            latest_diff_snapshot_id=digest.get('latest_diff_snapshot_id'),
            correlated_run_id=correlated_run_id,
        )

        rows.append(
            {
                'source_scope': scope,
                'alert_status': alert.get('alert_status', ALERT_STATUS_MINOR_CHANGE),
                'drift_status': digest['latest_drift_status'],
                'attention_priority': alert.get('alert_status', ALERT_STATUS_MINOR_CHANGE),
                'latest_diff_snapshot_id': digest.get('latest_diff_snapshot_id'),
                'latest_diff_status': digest.get('latest_diff_status'),
                'latest_diff_summary': digest.get('latest_diff_summary'),
                'correlated_run_id': correlated_run_id,
                'correlated_run_timestamp': correlated_run_timestamp,
                'correlated_profile_name': correlation.get('tuning_profile_name') if correlated_run_id else None,
                'correlated_profile_fingerprint': correlation.get('tuning_profile_fingerprint') if correlated_run_id else None,
                'changed_field_count': review.changed_field_count,
                'changed_guardrail_count': review.changed_guardrail_count,
                'review_reason_codes': review.review_reason_codes,
                'recommended_next_action': review.recommended_next_action,
                'board_summary': review.board_summary,
                '_sort_created_at': diff.get('created_at') or digest.get('latest_snapshot_created_at'),
            }
        )
    return rows


def _ordered_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def _created_sort_value(row: dict[str, Any]) -> float:
        created_at = row.get('_sort_created_at')
        if hasattr(created_at, 'timestamp'):
            return float(created_at.timestamp())
        return 0.0

    ordered = sorted(
        rows,
        key=lambda row: (
            -ATTENTION_PRIORITY_ORDER.get(str(row.get('attention_priority')), 0),
            -int(row.get('changed_guardrail_count') or 0),
            -int(row.get('changed_field_count') or 0),
            -_created_sort_value(row),
            str(row.get('source_scope') or ''),
        ),
    )
    for index, row in enumerate(ordered, start=1):
        row['attention_rank'] = index
        row.pop('_sort_created_at', None)
    return ordered


def build_tuning_review_board(
    *,
    source_scope: str | None = None,
    attention_only: bool = False,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    rows = _build_base_rows(source_scope=source_scope)
    ordered = _ordered_rows(rows)

    if attention_only:
        ordered = [row for row in ordered if row['attention_priority'] != ALERT_STATUS_STABLE]

    if limit is not None:
        ordered = ordered[: max(limit, 0)]

    return ordered


def get_tuning_review_board_detail(*, source_scope: str) -> dict[str, Any] | None:
    rows = build_tuning_review_board(source_scope=source_scope)
    return rows[0] if rows else None

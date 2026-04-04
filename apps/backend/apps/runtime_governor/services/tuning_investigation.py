from __future__ import annotations

from typing import Any

from apps.runtime_governor.models import RuntimeTuningContextSnapshot
from apps.runtime_governor.services.tuning_alerts import ALERT_STATUS_MINOR_CHANGE, build_tuning_change_alerts
from apps.runtime_governor.services.tuning_correlation import build_tuning_run_correlations
from apps.runtime_governor.services.tuning_diff import build_tuning_context_diffs
from apps.runtime_governor.services.tuning_digest import build_tuning_scope_digest
from apps.runtime_governor.services.tuning_links import build_latest_diff_links
from apps.runtime_governor.services.tuning_review_board import get_tuning_review_board_detail

PREVIEW_LIMIT = 5


def _runtime_deep_link(source_scope: str) -> str:
    return f'/runtime?tuningScope={source_scope}&investigate=1'


def _runtime_diff_deep_link(*, source_scope: str, snapshot_id: int | None) -> str:
    if snapshot_id is None:
        return _runtime_deep_link(source_scope)
    return f'/runtime?tuningScope={source_scope}&investigate=1&diffSnapshotId={snapshot_id}'


def _build_investigation_summary(
    *,
    source_scope: str,
    attention_priority: str,
    alert_status: str,
    drift_status: str,
    changed_field_count: int,
    changed_guardrail_count: int,
    has_correlated_run: bool,
    recommended_next_action: str,
) -> str:
    correlation_clause = 'correlated run available' if has_correlated_run else 'no correlated run'
    return (
        f'{source_scope}: priority {attention_priority}, alert {alert_status}, drift {drift_status}; '
        f'{changed_field_count} changed field(s), {changed_guardrail_count} guardrail change(s); '
        f'{correlation_clause}. Next action: {recommended_next_action}.'
    )


def get_tuning_investigation_packet(*, source_scope: str) -> dict[str, Any] | None:
    digest_rows = build_tuning_scope_digest(source_scope=source_scope)
    if not digest_rows:
        return None

    digest_row = digest_rows[0]
    latest_snapshot = RuntimeTuningContextSnapshot.objects.filter(id=digest_row['latest_snapshot_id']).first()
    if latest_snapshot is None:
        return None

    review_row = get_tuning_review_board_detail(source_scope=source_scope) or {}
    alert_row = (build_tuning_change_alerts(source_scope=source_scope) or [{}])[0]
    diff_row = build_tuning_context_diffs(snapshots=[latest_snapshot])[0]
    links_by_scope = build_latest_diff_links(latest_snapshots=[latest_snapshot])
    latest_diff_link = links_by_scope.get(
        source_scope,
        {
            'latest_diff_snapshot_id': None,
            'latest_diff_status': None,
            'latest_diff_summary': None,
        },
    )

    has_comparable_diff = diff_row.get('previous_snapshot_id') is not None and latest_diff_link.get('latest_diff_snapshot_id') is not None
    changed_fields = diff_row.get('changed_fields', {}) if has_comparable_diff else {}
    changed_field_names = sorted(changed_fields.keys())
    changed_guardrail_field_names = [name for name in changed_field_names if name.startswith('guardrails.')]

    changed_fields_preview = changed_field_names[:PREVIEW_LIMIT]
    changed_guardrail_fields_preview = changed_guardrail_field_names[:PREVIEW_LIMIT]

    correlations = build_tuning_run_correlations(snapshots=[latest_snapshot])
    correlation_row = correlations[0] if correlations else {}
    correlated_run_timestamp = correlation_row.get('run_created_at')
    correlated_run_id = correlation_row.get('source_run_id') if correlated_run_timestamp else None
    has_correlated_run = correlated_run_id is not None

    attention_priority = review_row.get('attention_priority') or alert_row.get('alert_status') or ALERT_STATUS_MINOR_CHANGE
    alert_status = review_row.get('alert_status') or alert_row.get('alert_status') or ALERT_STATUS_MINOR_CHANGE
    drift_status = review_row.get('drift_status') or digest_row.get('latest_drift_status')
    recommended_next_action = review_row.get('recommended_next_action') or 'MONITOR_ONLY'

    return {
        'source_scope': source_scope,
        'attention_priority': attention_priority,
        'attention_rank': review_row.get('attention_rank', 1),
        'alert_status': alert_status,
        'drift_status': drift_status,
        'board_summary': review_row.get('board_summary') or '',
        'review_reason_codes': review_row.get('review_reason_codes', []),
        'recommended_next_action': recommended_next_action,
        'investigation_summary': _build_investigation_summary(
            source_scope=source_scope,
            attention_priority=attention_priority,
            alert_status=alert_status,
            drift_status=drift_status,
            changed_field_count=len(changed_field_names) if has_comparable_diff else 0,
            changed_guardrail_count=len(changed_guardrail_field_names) if has_comparable_diff else 0,
            has_correlated_run=has_correlated_run,
            recommended_next_action=recommended_next_action,
        ),
        'latest_diff_snapshot_id': latest_diff_link.get('latest_diff_snapshot_id') if has_comparable_diff else None,
        'latest_diff_status': latest_diff_link.get('latest_diff_status') if has_comparable_diff else None,
        'latest_diff_summary': latest_diff_link.get('latest_diff_summary') if has_comparable_diff else None,
        'changed_field_count': len(changed_field_names) if has_comparable_diff else 0,
        'changed_guardrail_count': len(changed_guardrail_field_names) if has_comparable_diff else 0,
        'changed_fields_preview': changed_fields_preview if has_comparable_diff else [],
        'changed_guardrail_fields_preview': changed_guardrail_fields_preview if has_comparable_diff else [],
        'changed_fields_remaining_count': max(len(changed_field_names) - len(changed_fields_preview), 0) if has_comparable_diff else 0,
        'changed_guardrail_remaining_count': max(len(changed_guardrail_field_names) - len(changed_guardrail_fields_preview), 0)
        if has_comparable_diff
        else 0,
        'correlated_run_id': correlated_run_id,
        'correlated_run_timestamp': correlated_run_timestamp if has_correlated_run else None,
        'correlated_profile_name': correlation_row.get('tuning_profile_name') if has_correlated_run else None,
        'correlated_profile_fingerprint': correlation_row.get('tuning_profile_fingerprint') if has_correlated_run else None,
        'correlated_run_summary': correlation_row.get('correlation_summary') if has_correlated_run else None,
        'latest_snapshot_id': digest_row.get('latest_snapshot_id'),
        'latest_snapshot_created_at': digest_row.get('latest_snapshot_created_at'),
        'previous_snapshot_id': diff_row.get('previous_snapshot_id'),
        'has_comparable_diff': has_comparable_diff,
        'has_correlated_run': has_correlated_run,
        'runtime_deep_link': _runtime_deep_link(source_scope),
        'runtime_diff_deep_link': _runtime_diff_deep_link(
            source_scope=source_scope,
            snapshot_id=latest_diff_link.get('latest_diff_snapshot_id') if has_comparable_diff else None,
        ),
    }

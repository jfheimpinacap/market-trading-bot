from __future__ import annotations

from typing import Any

from django.utils import timezone

from apps.runtime_governor.services.tuning_alert_summary import build_tuning_alert_summary
from apps.runtime_governor.services.tuning_review_board import build_tuning_review_board, get_tuning_review_board_detail

NO_ATTENTION_SUMMARY = 'No runtime tuning attention required.'


def _runtime_deep_link(source_scope: str) -> str:
    return f'/runtime?tuningScope={source_scope}'


def _to_panel_item(row: dict[str, Any]) -> dict[str, Any]:
    return {
        'source_scope': row['source_scope'],
        'attention_priority': row['attention_priority'],
        'attention_rank': row['attention_rank'],
        'alert_status': row['alert_status'],
        'drift_status': row['drift_status'],
        'board_summary': row['board_summary'],
        'recommended_next_action': row['recommended_next_action'],
        'latest_diff_snapshot_id': row['latest_diff_snapshot_id'],
        'latest_diff_status': row['latest_diff_status'],
        'latest_diff_summary': row['latest_diff_summary'],
        'correlated_run_id': row['correlated_run_id'],
        'correlated_run_timestamp': row['correlated_run_timestamp'],
        'correlated_profile_name': row['correlated_profile_name'],
        'correlated_profile_fingerprint': row['correlated_profile_fingerprint'],
        'runtime_deep_link': _runtime_deep_link(row['source_scope']),
    }


def build_tuning_cockpit_panel(
    *,
    source_scope: str | None = None,
    attention_only: bool = True,
    limit: int = 5,
) -> dict[str, Any]:
    alert_summary = build_tuning_alert_summary(source_scope=source_scope)
    rows = build_tuning_review_board(source_scope=source_scope, attention_only=attention_only, limit=limit)
    items = [_to_panel_item(row) for row in rows]
    highest = items[0] if items else None

    return {
        'generated_at': timezone.now(),
        'total_scope_count': alert_summary['total_scope_count'],
        'attention_scope_count': alert_summary['total_scope_count'] - alert_summary['stable_count'],
        'highest_priority_scope': highest['source_scope'] if highest else None,
        'highest_priority_status': highest['attention_priority'] if highest else None,
        'panel_summary': alert_summary['summary'] if items else NO_ATTENTION_SUMMARY,
        'items': items,
    }


def get_tuning_cockpit_panel_detail(*, source_scope: str) -> dict[str, Any] | None:
    row = get_tuning_review_board_detail(source_scope=source_scope)
    if not row:
        return None

    detail = _to_panel_item(row)
    detail['review_reason_codes'] = row['review_reason_codes']
    detail['changed_field_count'] = row['changed_field_count']
    detail['changed_guardrail_count'] = row['changed_guardrail_count']
    return detail

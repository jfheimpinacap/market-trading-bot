from __future__ import annotations

from typing import Any

from django.utils import timezone

from apps.runtime_governor.models import RuntimeTuningReviewStatus
from apps.runtime_governor.services.tuning_review_activity import build_tuning_review_activity
from apps.runtime_governor.services.tuning_review_aging import AGE_BUCKET_OVERDUE, build_tuning_review_aging
from apps.runtime_governor.services.tuning_review_escalation import (
    ESCALATION_LEVEL_ELEVATED,
    ESCALATION_LEVEL_URGENT,
    build_tuning_review_escalation,
)
from apps.runtime_governor.services.tuning_review_queue import build_tuning_review_queue
from apps.runtime_governor.services.tuning_review_state import TuningScopeSnapshotNotFound

DEFAULT_AUTOTRIAGE_TOP_N = 3

MODE_REVIEW_NOW = 'REVIEW_NOW'
MODE_REVIEW_SOON = 'REVIEW_SOON'
MODE_MONITOR_ONLY = 'MONITOR_ONLY'
MODE_NO_ACTION = 'NO_ACTION'


def _collect_rows_by_scope(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row['source_scope']): row for row in rows}


def _build_top_scope_item(scope: str, *, escalation_by_scope: dict[str, dict[str, Any]], aging_by_scope: dict[str, dict[str, Any],], queue_by_scope: dict[str, dict[str, Any]]) -> dict[str, Any]:
    escalation_row = escalation_by_scope.get(scope)
    if escalation_row:
        return {
            'source_scope': scope,
            'effective_review_status': escalation_row['effective_review_status'],
            'attention_priority': escalation_row['attention_priority'],
            'age_bucket': escalation_row['age_bucket'],
            'escalation_level': escalation_row['escalation_level'],
            'requires_immediate_attention': escalation_row['requires_immediate_attention'],
            'review_summary': escalation_row['review_summary'],
            'technical_summary': escalation_row['technical_summary'],
            'runtime_investigation_deep_link': escalation_row['runtime_investigation_deep_link'],
            'age_days': escalation_row.get('age_days'),
            'last_action_at': escalation_row.get('last_action_at'),
        }

    aging_row = aging_by_scope.get(scope)
    if aging_row:
        return {
            'source_scope': scope,
            'effective_review_status': aging_row['effective_review_status'],
            'attention_priority': aging_row['attention_priority'],
            'age_bucket': aging_row['age_bucket'],
            'escalation_level': 'MONITOR',
            'requires_immediate_attention': False,
            'review_summary': aging_row['review_summary'],
            'technical_summary': aging_row['technical_summary'],
            'runtime_investigation_deep_link': aging_row['runtime_investigation_deep_link'],
            'age_days': aging_row.get('age_days'),
            'last_action_at': aging_row.get('last_action_at'),
        }

    queue_row = queue_by_scope.get(scope)
    if queue_row:
        return {
            'source_scope': scope,
            'effective_review_status': queue_row['effective_review_status'],
            'attention_priority': queue_row['attention_priority'],
            'age_bucket': 'FRESH',
            'escalation_level': 'MONITOR',
            'requires_immediate_attention': False,
            'review_summary': queue_row['review_summary'],
            'technical_summary': queue_row['technical_summary'],
            'runtime_investigation_deep_link': queue_row['runtime_investigation_deep_link'],
            'age_days': None,
            'last_action_at': queue_row.get('last_action_at'),
        }

    raise TuningScopeSnapshotNotFound(scope)


def _resolve_human_attention_mode(*, urgent_count: int, elevated_count: int, overdue_count: int, followup_count: int, unresolved_count: int) -> str:
    if urgent_count > 0:
        return MODE_REVIEW_NOW
    if elevated_count > 0 or overdue_count > 0 or followup_count > 0:
        return MODE_REVIEW_SOON
    if unresolved_count > 0:
        return MODE_MONITOR_ONLY
    return MODE_NO_ACTION


def _resolve_recommended_scope(*, escalation_items: list[dict[str, Any]], aging_items: list[dict[str, Any]], queue_items: list[dict[str, Any]]) -> tuple[str | None, list[str]]:
    urgent = next((item for item in escalation_items if item['escalation_level'] == ESCALATION_LEVEL_URGENT), None)
    if urgent:
        return str(urgent['source_scope']), ['URGENT_SCOPE_PRESENT']

    overdue = next((item for item in aging_items if item['age_bucket'] == AGE_BUCKET_OVERDUE), None)
    if overdue:
        return str(overdue['source_scope']), ['OVERDUE_SCOPE_PRESENT']

    followup = next(
        (item for item in queue_items if item['effective_review_status'] == RuntimeTuningReviewStatus.FOLLOWUP_REQUIRED),
        None,
    )
    if followup:
        return str(followup['source_scope']), ['FOLLOWUP_PENDING']

    unresolved = next((item for item in queue_items), None)
    if unresolved:
        return str(unresolved['source_scope']), ['STALE_REVIEW_PENDING']

    return None, ['NO_UNRESOLVED_SCOPES']


def _resolve_summary(*, mode: str, next_scope: str | None) -> str:
    if mode == MODE_REVIEW_NOW:
        return f'Human review is required now; next focus is {next_scope}' if next_scope else 'Human review is required now'
    if mode == MODE_REVIEW_SOON:
        return 'No urgent runtime tuning reviews; review can be deferred with follow-up soon'
    if mode == MODE_MONITOR_ONLY:
        return 'Only monitor-level unresolved items remain'
    return 'No runtime tuning review action required now'


def _resolve_can_defer(mode: str) -> bool:
    if mode == MODE_REVIEW_NOW:
        return False
    return True


def build_tuning_autotriage_digest(*, top_n: int = DEFAULT_AUTOTRIAGE_TOP_N, include_monitor: bool = False) -> dict[str, Any]:
    safe_top_n = max(0, min(int(top_n), DEFAULT_AUTOTRIAGE_TOP_N))

    queue = build_tuning_review_queue(unresolved_only=True, limit=1000)
    aging = build_tuning_review_aging(unresolved_only=True, limit=1000)
    escalation = build_tuning_review_escalation(escalated_only=False, limit=1000)
    activity = build_tuning_review_activity(limit=10)

    unresolved_items = list(queue.get('items', []))
    escalation_items = list(escalation.get('items', []))
    aging_items = list(aging.get('items', []))

    unresolved_count = int(queue.get('queue_count', 0))
    urgent_count = int(escalation.get('urgent_count', 0))
    overdue_count = int(aging.get('overdue_count', 0))
    elevated_count = int(escalation.get('elevated_count', 0))
    followup_count = int(queue.get('followup_count', 0))

    human_attention_mode = _resolve_human_attention_mode(
        urgent_count=urgent_count,
        elevated_count=elevated_count,
        overdue_count=overdue_count,
        followup_count=followup_count,
        unresolved_count=unresolved_count,
    )

    next_scope, reason_codes = _resolve_recommended_scope(
        escalation_items=escalation_items,
        aging_items=aging_items,
        queue_items=unresolved_items,
    )

    if human_attention_mode == MODE_MONITOR_ONLY and reason_codes == ['STALE_REVIEW_PENDING']:
        reason_codes = ['RECENT_ACTIVITY_ONLY'] if int(activity.get('activity_count', 0)) > 0 else ['STALE_REVIEW_PENDING']

    escalation_by_scope = _collect_rows_by_scope(escalation_items)
    aging_by_scope = _collect_rows_by_scope(aging_items)
    queue_by_scope = _collect_rows_by_scope(unresolved_items)

    ordered_candidates = escalation_items if include_monitor else [
        item for item in escalation_items if item['escalation_level'] in {ESCALATION_LEVEL_URGENT, ESCALATION_LEVEL_ELEVATED}
    ]
    if not ordered_candidates:
        ordered_candidates = escalation_items

    top_scope_ids = [str(item['source_scope']) for item in ordered_candidates[:safe_top_n]]
    top_scopes = [
        _build_top_scope_item(
            scope,
            escalation_by_scope=escalation_by_scope,
            aging_by_scope=aging_by_scope,
            queue_by_scope=queue_by_scope,
        )
        for scope in top_scope_ids
    ]

    if next_scope and next_scope not in top_scope_ids and len(top_scopes) < safe_top_n:
        top_scopes.append(
            _build_top_scope_item(
                next_scope,
                escalation_by_scope=escalation_by_scope,
                aging_by_scope=aging_by_scope,
                queue_by_scope=queue_by_scope,
            )
        )

    return {
        'generated_at': timezone.now(),
        'human_attention_mode': human_attention_mode,
        'requires_human_now': human_attention_mode == MODE_REVIEW_NOW,
        'can_defer_human_review': _resolve_can_defer(human_attention_mode),
        'unresolved_count': unresolved_count,
        'urgent_count': urgent_count,
        'overdue_count': overdue_count,
        'recent_activity_count': int(activity.get('activity_count', 0)),
        'next_recommended_scope': next_scope,
        'next_recommended_reason_codes': reason_codes,
        'autotriage_summary': _resolve_summary(mode=human_attention_mode, next_scope=next_scope),
        'top_scopes': top_scopes,
    }


def get_tuning_autotriage_digest_detail(*, source_scope: str, include_monitor: bool = False) -> dict[str, Any]:
    payload = build_tuning_autotriage_digest(top_n=DEFAULT_AUTOTRIAGE_TOP_N, include_monitor=include_monitor)
    for item in payload['top_scopes']:
        if item['source_scope'] == source_scope:
            return {
                **item,
                'generated_at': payload['generated_at'],
                'human_attention_mode': payload['human_attention_mode'],
                'next_recommended_scope': payload['next_recommended_scope'],
                'next_recommended_reason_codes': payload['next_recommended_reason_codes'],
            }

    queue = build_tuning_review_queue(unresolved_only=False, limit=1000)
    queue_row = next((item for item in queue.get('items', []) if item['source_scope'] == source_scope), None)
    if not queue_row:
        raise TuningScopeSnapshotNotFound(source_scope)

    escalation = build_tuning_review_escalation(escalated_only=False, limit=1000)
    aging = build_tuning_review_aging(unresolved_only=False, limit=1000)
    item = _build_top_scope_item(
        source_scope,
        escalation_by_scope=_collect_rows_by_scope(escalation.get('items', [])),
        aging_by_scope=_collect_rows_by_scope(aging.get('items', [])),
        queue_by_scope={source_scope: queue_row},
    )
    return {
        **item,
        'generated_at': payload['generated_at'],
        'human_attention_mode': payload['human_attention_mode'],
        'next_recommended_scope': payload['next_recommended_scope'],
        'next_recommended_reason_codes': payload['next_recommended_reason_codes'],
    }

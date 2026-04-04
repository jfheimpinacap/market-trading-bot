from __future__ import annotations

from datetime import datetime
from typing import Any

from apps.runtime_governor.models import RuntimeTuningReviewStatus
from apps.runtime_governor.services.tuning_review_board import build_tuning_review_board
from apps.runtime_governor.services.tuning_review_state import (
    SUMMARY_BY_STATUS,
    TuningScopeSnapshotNotFound,
    get_tuning_review_state_detail,
    list_tuning_review_states,
)

DEFAULT_QUEUE_LIMIT = 8

STATUS_ORDER = {
    RuntimeTuningReviewStatus.FOLLOWUP_REQUIRED: 0,
    RuntimeTuningReviewStatus.STALE_REVIEW: 1,
    RuntimeTuningReviewStatus.UNREVIEWED: 2,
    RuntimeTuningReviewStatus.ACKNOWLEDGED_CURRENT: 3,
}

TECHNICAL_PRIORITY_ORDER = {
    'REVIEW_NOW': 0,
    'PROFILE_SHIFT': 1,
    'MINOR_CHANGE': 2,
    'STABLE': 3,
}

TECHNICAL_REASON_CODES = {
    'REVIEW_NOW': 'TECHNICAL_REVIEW_NOW',
    'PROFILE_SHIFT': 'TECHNICAL_PROFILE_SHIFT',
    'MINOR_CHANGE': 'TECHNICAL_MINOR_CHANGE',
}


def _parse_last_action(value: Any) -> tuple[int, datetime]:
    if not value:
        return (1, datetime.min)
    if isinstance(value, datetime):
        return (0, value)
    return (0, datetime.min)


def _build_item(row: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    effective_review_status = str(state['effective_review_status'])
    technical_priority = str(row['attention_priority'])

    reason_codes: list[str] = []
    if effective_review_status == RuntimeTuningReviewStatus.FOLLOWUP_REQUIRED:
        reason_codes.append('FOLLOWUP_REQUIRED')
    elif effective_review_status == RuntimeTuningReviewStatus.STALE_REVIEW:
        reason_codes.append('STALE_REVIEW')
    elif effective_review_status == RuntimeTuningReviewStatus.UNREVIEWED:
        reason_codes.append('UNREVIEWED_SCOPE')
    else:
        reason_codes.append('ACKNOWLEDGED_CURRENT')

    technical_reason_code = TECHNICAL_REASON_CODES.get(technical_priority)
    if technical_reason_code:
        reason_codes.append(technical_reason_code)

    requires_manual_attention = effective_review_status in {
        RuntimeTuningReviewStatus.FOLLOWUP_REQUIRED,
        RuntimeTuningReviewStatus.STALE_REVIEW,
        RuntimeTuningReviewStatus.UNREVIEWED,
    }

    return {
        'source_scope': row['source_scope'],
        'effective_review_status': effective_review_status,
        'attention_priority': technical_priority,
        'queue_rank': 0,
        'requires_manual_attention': requires_manual_attention,
        'queue_reason_codes': reason_codes,
        'technical_summary': row['board_summary'],
        'review_summary': state['review_summary'],
        'last_action_type': state.get('last_action_type', ''),
        'last_action_at': state.get('last_action_at'),
        'has_newer_snapshot_than_reviewed': bool(state.get('has_newer_snapshot_than_reviewed')),
        'runtime_deep_link': state['runtime_deep_link'],
        'runtime_investigation_deep_link': state['runtime_investigation_deep_link'],
        'latest_snapshot_id': state.get('latest_snapshot_id'),
        'last_reviewed_snapshot_id': state.get('last_reviewed_snapshot_id'),
        'stored_review_status': state.get('stored_review_status'),
    }


def _build_queue_summary(*, queue_count: int, unreviewed_count: int, followup_count: int, stale_count: int, unresolved_only: bool) -> str:
    if queue_count == 0:
        return 'No unresolved runtime tuning reviews' if unresolved_only else 'No runtime tuning reviews in queue'

    if queue_count == unreviewed_count and followup_count == 0 and stale_count == 0:
        plural = 'scopes' if unreviewed_count != 1 else 'scope'
        return f'{unreviewed_count} unreviewed {plural} remain in technical attention queue'

    plural = 'scopes' if queue_count != 1 else 'scope'
    return f'{queue_count} {plural} require human review, including {stale_count} stale and {followup_count} follow-up'


def _sorted_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered = sorted(
        items,
        key=lambda item: (
            STATUS_ORDER.get(str(item['effective_review_status']), 99),
            TECHNICAL_PRIORITY_ORDER.get(str(item['attention_priority']), 99),
            _parse_last_action(item.get('last_action_at')),
            str(item['source_scope']),
        ),
    )
    for idx, item in enumerate(ordered, start=1):
        item['queue_rank'] = idx
    return ordered


def build_tuning_review_queue(
    *,
    unresolved_only: bool = True,
    effective_review_status: str | None = None,
    limit: int = DEFAULT_QUEUE_LIMIT,
) -> dict[str, Any]:
    board_rows = build_tuning_review_board(attention_only=False)
    review_states = list_tuning_review_states()
    review_state_by_scope = {row['source_scope']: row for row in review_states}

    items: list[dict[str, Any]] = []
    for row in board_rows:
        scope = row['source_scope']
        review_state = review_state_by_scope.get(scope)
        if not review_state:
            continue
        queue_item = _build_item(row, review_state)
        if unresolved_only and queue_item['effective_review_status'] == RuntimeTuningReviewStatus.ACKNOWLEDGED_CURRENT:
            continue
        if effective_review_status and queue_item['effective_review_status'] != effective_review_status:
            continue
        items.append(queue_item)

    sorted_items = _sorted_items(items)
    queue_items = sorted_items[: max(limit, 0)]

    unreviewed_count = sum(1 for item in sorted_items if item['effective_review_status'] == RuntimeTuningReviewStatus.UNREVIEWED)
    followup_count = sum(1 for item in sorted_items if item['effective_review_status'] == RuntimeTuningReviewStatus.FOLLOWUP_REQUIRED)
    stale_count = sum(1 for item in sorted_items if item['effective_review_status'] == RuntimeTuningReviewStatus.STALE_REVIEW)

    return {
        'total_scope_count': len(review_states),
        'queue_count': len(sorted_items),
        'unreviewed_count': unreviewed_count,
        'followup_count': followup_count,
        'stale_count': stale_count,
        'highest_priority_scope': sorted_items[0]['source_scope'] if sorted_items else None,
        'queue_summary': _build_queue_summary(
            queue_count=len(sorted_items),
            unreviewed_count=unreviewed_count,
            followup_count=followup_count,
            stale_count=stale_count,
            unresolved_only=unresolved_only,
        ),
        'items': queue_items,
    }


def get_tuning_review_queue_detail(*, source_scope: str) -> dict[str, Any]:
    state = get_tuning_review_state_detail(source_scope=source_scope)
    board_rows = build_tuning_review_board(source_scope=source_scope, attention_only=False)
    if not board_rows:
        raise TuningScopeSnapshotNotFound(source_scope)

    item = _build_item(board_rows[0], state)
    item['queue_rank'] = 1
    item['queue_summary'] = SUMMARY_BY_STATUS.get(item['effective_review_status'], state['review_summary'])
    return item

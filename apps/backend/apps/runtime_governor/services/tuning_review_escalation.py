from __future__ import annotations

from typing import Any

from apps.runtime_governor.models import RuntimeTuningReviewStatus
from apps.runtime_governor.services.tuning_review_aging import (
    AGE_BUCKET_AGING,
    AGE_BUCKET_OVERDUE,
    build_tuning_review_aging,
    get_tuning_review_aging_detail,
)
from apps.runtime_governor.services.tuning_review_state import TuningScopeSnapshotNotFound

ESCALATION_LEVEL_MONITOR = 'MONITOR'
ESCALATION_LEVEL_ELEVATED = 'ELEVATED'
ESCALATION_LEVEL_URGENT = 'URGENT'

ESCALATION_RANK = {
    ESCALATION_LEVEL_URGENT: 1,
    ESCALATION_LEVEL_ELEVATED: 2,
    ESCALATION_LEVEL_MONITOR: 3,
}

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


def _compute_escalation(item: dict[str, Any]) -> tuple[str, list[str]]:
    status = str(item['effective_review_status'])
    age_bucket = str(item['age_bucket'])
    priority = str(item['attention_priority'])

    if status == RuntimeTuningReviewStatus.FOLLOWUP_REQUIRED and age_bucket == AGE_BUCKET_OVERDUE:
        return ESCALATION_LEVEL_URGENT, ['FOLLOWUP_OVERDUE']
    if status == RuntimeTuningReviewStatus.STALE_REVIEW and age_bucket == AGE_BUCKET_OVERDUE:
        return ESCALATION_LEVEL_URGENT, ['STALE_OVERDUE']
    if status == RuntimeTuningReviewStatus.UNREVIEWED and age_bucket == AGE_BUCKET_OVERDUE and priority == 'REVIEW_NOW':
        return ESCALATION_LEVEL_URGENT, ['UNREVIEWED_REVIEW_NOW_OVERDUE']

    if status == RuntimeTuningReviewStatus.FOLLOWUP_REQUIRED and age_bucket == AGE_BUCKET_AGING:
        return ESCALATION_LEVEL_ELEVATED, ['FOLLOWUP_AGING']
    if status == RuntimeTuningReviewStatus.STALE_REVIEW and age_bucket == AGE_BUCKET_AGING:
        return ESCALATION_LEVEL_ELEVATED, ['STALE_AGING']
    if status == RuntimeTuningReviewStatus.UNREVIEWED and age_bucket == AGE_BUCKET_OVERDUE:
        return ESCALATION_LEVEL_ELEVATED, ['UNREVIEWED_OVERDUE']
    if status == RuntimeTuningReviewStatus.UNREVIEWED and age_bucket == AGE_BUCKET_AGING and priority in {'REVIEW_NOW', 'PROFILE_SHIFT'}:
        return ESCALATION_LEVEL_ELEVATED, ['UNREVIEWED_PROFILE_SHIFT']

    return ESCALATION_LEVEL_MONITOR, ['MONITOR_ONLY']


def _enrich_item(item: dict[str, Any]) -> dict[str, Any]:
    level, reason_codes = _compute_escalation(item)
    return {
        **item,
        'escalation_level': level,
        'escalation_rank': ESCALATION_RANK[level],
        'requires_immediate_attention': level == ESCALATION_LEVEL_URGENT,
        'escalation_reason_codes': reason_codes,
    }


def _sort_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        items,
        key=lambda item: (
            ESCALATION_RANK.get(str(item['escalation_level']), 99),
            STATUS_ORDER.get(str(item['effective_review_status']), 99),
            TECHNICAL_PRIORITY_ORDER.get(str(item['attention_priority']), 99),
            -int(item['age_days']),
            str(item['source_scope']),
        ),
    )


def _build_escalation_summary(*, urgent_count: int, elevated_count: int, escalated_count: int) -> str:
    if escalated_count == 0:
        return 'No escalated runtime tuning reviews'
    if elevated_count == 0:
        review_label = 'review' if urgent_count == 1 else 'reviews'
        return f'{urgent_count} urgent tuning {review_label} require immediate attention'
    return f'{urgent_count} urgent and {elevated_count} elevated tuning reviews are pending'


def build_tuning_review_escalation(
    *,
    escalated_only: bool = True,
    escalation_level: str | None = None,
    limit: int = 6,
) -> dict[str, Any]:
    aging = build_tuning_review_aging(unresolved_only=True, age_bucket=None, limit=1000)
    queue_count = int(aging.get('queue_count', 0))
    items = [_enrich_item(item) for item in aging.get('items', [])]

    urgent_count = sum(1 for item in items if item['escalation_level'] == ESCALATION_LEVEL_URGENT)
    elevated_count = sum(1 for item in items if item['escalation_level'] == ESCALATION_LEVEL_ELEVATED)
    monitor_count = sum(1 for item in items if item['escalation_level'] == ESCALATION_LEVEL_MONITOR)
    escalated_count = urgent_count + elevated_count

    filtered_items = items
    if escalated_only:
        filtered_items = [item for item in filtered_items if item['escalation_level'] in {ESCALATION_LEVEL_URGENT, ESCALATION_LEVEL_ELEVATED}]
    if escalation_level:
        normalized = str(escalation_level).upper()
        filtered_items = [item for item in filtered_items if item['escalation_level'] == normalized]

    ordered = _sort_items(filtered_items)
    limited_items = ordered[: max(limit, 0)]

    return {
        'queue_count': queue_count,
        'escalated_count': escalated_count,
        'urgent_count': urgent_count,
        'elevated_count': elevated_count,
        'monitor_count': monitor_count,
        'highest_escalation_scope': ordered[0]['source_scope'] if ordered else None,
        'escalation_summary': _build_escalation_summary(
            urgent_count=urgent_count,
            elevated_count=elevated_count,
            escalated_count=escalated_count,
        ),
        'items': limited_items,
    }


def get_tuning_review_escalation_detail(*, source_scope: str) -> dict[str, Any]:
    try:
        detail = get_tuning_review_aging_detail(source_scope=source_scope)
    except TuningScopeSnapshotNotFound:
        raise
    enriched = _enrich_item(detail)
    return {
        **enriched,
        'escalation_summary': _build_escalation_summary(
            urgent_count=1 if enriched['escalation_level'] == ESCALATION_LEVEL_URGENT else 0,
            elevated_count=1 if enriched['escalation_level'] == ESCALATION_LEVEL_ELEVATED else 0,
            escalated_count=0 if enriched['escalation_level'] == ESCALATION_LEVEL_MONITOR else 1,
        ),
    }

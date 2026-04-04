from __future__ import annotations

from datetime import datetime
from typing import Any

from django.utils import timezone

from apps.runtime_governor.models import RuntimeTuningContextSnapshot, RuntimeTuningReviewStatus
from apps.runtime_governor.services.tuning_review_queue import DEFAULT_QUEUE_LIMIT, build_tuning_review_queue
from apps.runtime_governor.services.tuning_review_state import TuningScopeSnapshotNotFound, get_tuning_review_state_detail

AGE_BUCKET_FRESH = 'FRESH'
AGE_BUCKET_AGING = 'AGING'
AGE_BUCKET_OVERDUE = 'OVERDUE'

AGE_BUCKET_ORDER = {
    AGE_BUCKET_OVERDUE: 0,
    AGE_BUCKET_AGING: 1,
    AGE_BUCKET_FRESH: 2,
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


def _resolve_age_bucket(age_days: int) -> str:
    if age_days >= 7:
        return AGE_BUCKET_OVERDUE
    if age_days >= 2:
        return AGE_BUCKET_AGING
    return AGE_BUCKET_FRESH


def _build_aging_reason_codes(*, effective_review_status: str, age_bucket: str) -> list[str]:
    if effective_review_status == RuntimeTuningReviewStatus.FOLLOWUP_REQUIRED:
        return ['FOLLOWUP_OVERDUE'] if age_bucket == AGE_BUCKET_OVERDUE else ['FOLLOWUP_AGING']
    if effective_review_status == RuntimeTuningReviewStatus.STALE_REVIEW:
        return ['STALE_REVIEW_OVERDUE'] if age_bucket == AGE_BUCKET_OVERDUE else ['STALE_REVIEW_PENDING']
    if effective_review_status == RuntimeTuningReviewStatus.UNREVIEWED:
        return ['UNREVIEWED_OVERDUE'] if age_bucket == AGE_BUCKET_OVERDUE else ['UNREVIEWED_AGING']
    return ['ACKNOWLEDGED_NOT_URGENT']


def _safe_age_days(*, age_reference_timestamp: datetime | None, now: datetime) -> int:
    if age_reference_timestamp is None:
        return 0
    delta = now - age_reference_timestamp
    return max(0, int(delta.days))


def _build_aging_summary(*, overdue_count: int, aging_count: int, followup_overdue_count: int) -> str:
    if overdue_count == 0:
        return 'No overdue human reviews in runtime tuning queue'
    if followup_overdue_count == 1 and aging_count > 0:
        scope_label = 'scope is' if aging_count == 1 else 'scopes are'
        return f'1 follow-up is overdue and {aging_count} {scope_label} aging'
    if followup_overdue_count > 1 and aging_count > 0:
        followup_label = 'follow-up is' if followup_overdue_count == 1 else 'follow-ups are'
        scope_label = 'scope is' if aging_count == 1 else 'scopes are'
        return f'{followup_overdue_count} {followup_label} overdue and {aging_count} {scope_label} aging'
    return f'{overdue_count} overdue runtime tuning reviews require attention'


def _build_age_reference_timestamp(
    *,
    item: dict[str, Any],
    latest_snapshot_timestamp: datetime | None,
) -> datetime | None:
    status_value = str(item['effective_review_status'])
    last_action_at = item.get('last_action_at')
    if status_value == RuntimeTuningReviewStatus.FOLLOWUP_REQUIRED:
        return last_action_at or latest_snapshot_timestamp
    if status_value == RuntimeTuningReviewStatus.ACKNOWLEDGED_CURRENT:
        return last_action_at or latest_snapshot_timestamp
    return latest_snapshot_timestamp


def _sorted_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered = sorted(
        items,
        key=lambda item: (
            AGE_BUCKET_ORDER.get(str(item['age_bucket']), 99),
            STATUS_ORDER.get(str(item['effective_review_status']), 99),
            TECHNICAL_PRIORITY_ORDER.get(str(item['attention_priority']), 99),
            -int(item['age_days']),
            str(item['source_scope']),
        ),
    )
    for idx, item in enumerate(ordered, start=1):
        item['aging_rank'] = idx
    return ordered


def build_tuning_review_aging(
    *,
    unresolved_only: bool = True,
    age_bucket: str | None = None,
    limit: int = DEFAULT_QUEUE_LIMIT,
) -> dict[str, Any]:
    queue = build_tuning_review_queue(unresolved_only=unresolved_only, effective_review_status=None, limit=1000)
    queue_items = queue.get('items', [])
    latest_snapshot_ids = [int(item['latest_snapshot_id']) for item in queue_items if item.get('latest_snapshot_id')]
    latest_snapshot_by_id = {
        snapshot.id: snapshot
        for snapshot in RuntimeTuningContextSnapshot.objects.filter(id__in=latest_snapshot_ids)
    }
    now = timezone.now()

    items: list[dict[str, Any]] = []
    for item in queue_items:
        latest_snapshot_id = item.get('latest_snapshot_id')
        latest_snapshot = latest_snapshot_by_id.get(int(latest_snapshot_id)) if latest_snapshot_id else None
        latest_snapshot_timestamp = latest_snapshot.created_at_snapshot if latest_snapshot else None
        age_reference_timestamp = _build_age_reference_timestamp(
            item=item,
            latest_snapshot_timestamp=latest_snapshot_timestamp,
        )
        age_days = _safe_age_days(age_reference_timestamp=age_reference_timestamp, now=now)
        computed_bucket = _resolve_age_bucket(age_days)
        enriched = {
            **item,
            'age_bucket': computed_bucket,
            'age_days': age_days,
            'overdue': computed_bucket == AGE_BUCKET_OVERDUE,
            'aging_rank': 0,
            'aging_reason_codes': _build_aging_reason_codes(
                effective_review_status=str(item['effective_review_status']),
                age_bucket=computed_bucket,
            ),
            'age_reference_timestamp': age_reference_timestamp,
        }
        items.append(enriched)

    if age_bucket:
        normalized_bucket = str(age_bucket).upper()
        items = [item for item in items if item['age_bucket'] == normalized_bucket]

    ordered = _sorted_items(items)
    limited_items = ordered[: max(limit, 0)]

    fresh_count = sum(1 for item in ordered if item['age_bucket'] == AGE_BUCKET_FRESH)
    aging_count = sum(1 for item in ordered if item['age_bucket'] == AGE_BUCKET_AGING)
    overdue_count = sum(1 for item in ordered if item['age_bucket'] == AGE_BUCKET_OVERDUE)
    followup_overdue_count = sum(
        1
        for item in ordered
        if item['age_bucket'] == AGE_BUCKET_OVERDUE and item['effective_review_status'] == RuntimeTuningReviewStatus.FOLLOWUP_REQUIRED
    )

    return {
        'queue_count': len(ordered),
        'fresh_count': fresh_count,
        'aging_count': aging_count,
        'overdue_count': overdue_count,
        'highest_urgency_scope': ordered[0]['source_scope'] if ordered else None,
        'aging_summary': _build_aging_summary(
            overdue_count=overdue_count,
            aging_count=aging_count,
            followup_overdue_count=followup_overdue_count,
        ),
        'items': limited_items,
    }


def get_tuning_review_aging_detail(*, source_scope: str) -> dict[str, Any]:
    state = get_tuning_review_state_detail(source_scope=source_scope)
    latest_snapshot = RuntimeTuningContextSnapshot.objects.filter(id=state['latest_snapshot_id']).first()
    if latest_snapshot is None:
        raise TuningScopeSnapshotNotFound(source_scope)
    queue = build_tuning_review_queue(unresolved_only=False, effective_review_status=None, limit=1000)
    queue_item = next((item for item in queue['items'] if item['source_scope'] == source_scope), None)
    if queue_item is None:
        raise TuningScopeSnapshotNotFound(source_scope)

    age_reference_timestamp = _build_age_reference_timestamp(
        item=queue_item,
        latest_snapshot_timestamp=latest_snapshot.created_at_snapshot,
    )
    age_days = _safe_age_days(age_reference_timestamp=age_reference_timestamp, now=timezone.now())
    resolved_bucket = _resolve_age_bucket(age_days)

    return {
        **queue_item,
        'age_bucket': resolved_bucket,
        'age_days': age_days,
        'overdue': resolved_bucket == AGE_BUCKET_OVERDUE,
        'aging_rank': 1,
        'age_reference_timestamp': age_reference_timestamp,
        'aging_reason_codes': _build_aging_reason_codes(
            effective_review_status=str(queue_item['effective_review_status']),
            age_bucket=resolved_bucket,
        ),
        'aging_summary': _build_aging_summary(
            overdue_count=1 if resolved_bucket == AGE_BUCKET_OVERDUE else 0,
            aging_count=1 if resolved_bucket == AGE_BUCKET_AGING else 0,
            followup_overdue_count=1 if (
                resolved_bucket == AGE_BUCKET_OVERDUE
                and str(queue_item['effective_review_status']) == RuntimeTuningReviewStatus.FOLLOWUP_REQUIRED
            ) else 0,
        ),
    }

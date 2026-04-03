from __future__ import annotations

from datetime import timedelta, timezone as dt_timezone

from django.utils import timezone

from apps.mission_control.models import (
    GovernanceBacklogPressureRun,
    GovernanceBacklogPressureSnapshot,
    GovernanceBacklogPressureState,
    GovernanceReviewItem,
    GovernanceReviewItemStatus,
    GovernanceReviewPriority,
)


def _contains_marker(values: list[str], markers: tuple[str, ...]) -> bool:
    upper_values = [str(value).upper() for value in values]
    return any(any(marker in value for marker in markers) for value in upper_values)


def _is_overdue(item: GovernanceReviewItem) -> bool:
    tags = [*item.reason_codes, *item.blockers]
    if _contains_marker(tags, ('OVERDUE', 'MANUAL_REVIEW_OVERDUE', 'REVIEW_OVERDUE')):
        return True
    due_at_raw = item.metadata.get('followup_due_at') or item.metadata.get('manual_review_due_at')
    if due_at_raw:
        try:
            due_at = timezone.datetime.fromisoformat(str(due_at_raw).replace('Z', '+00:00'))
            if timezone.is_naive(due_at):
                due_at = timezone.make_aware(due_at, timezone=dt_timezone.utc)
            return due_at <= timezone.now()
        except ValueError:
            return False
    return False


def _is_stale_blocked(item: GovernanceReviewItem) -> bool:
    tags = [*item.reason_codes, *item.blockers]
    is_blocked = _contains_marker(tags, ('BLOCK', 'STATUS_BLOCKED'))
    stale_cutoff = timezone.now() - timedelta(hours=72)
    is_stale = _contains_marker(tags, ('STALE', 'PERSISTENT')) or item.updated_at <= stale_cutoff
    return is_blocked and is_stale


def _is_followup_due(item: GovernanceReviewItem) -> bool:
    tags = [*item.reason_codes, *item.blockers]
    return _contains_marker(tags, ('FOLLOWUP', 'FOLLOW_UP', 'DUE'))


def _derive_pressure_state(*, open_count: int, in_review_count: int, p1_count: int, p2_count: int, overdue_count: int, stale_blocked_count: int, followup_due_count: int) -> tuple[str, list[str]]:
    reason_codes: list[str] = []
    active_count = open_count + in_review_count
    high_priority_count = p1_count + p2_count

    if active_count >= 20:
        reason_codes.append('active_backlog_very_high')
    elif active_count >= 12:
        reason_codes.append('active_backlog_elevated')

    if high_priority_count >= 10:
        reason_codes.append('high_priority_critical')
    elif high_priority_count >= 7:
        reason_codes.append('high_priority_high')
    elif high_priority_count >= 4:
        reason_codes.append('high_priority_caution')

    if overdue_count >= 6:
        reason_codes.append('overdue_critical')
    elif overdue_count >= 4:
        reason_codes.append('overdue_high')
    elif overdue_count >= 2:
        reason_codes.append('overdue_caution')

    if stale_blocked_count >= 4:
        reason_codes.append('stale_blocked_critical')
    elif stale_blocked_count >= 3:
        reason_codes.append('stale_blocked_high')
    elif stale_blocked_count >= 1:
        reason_codes.append('stale_blocked_present')

    if followup_due_count >= 8:
        reason_codes.append('followup_backlog_high')
    elif followup_due_count >= 5:
        reason_codes.append('followup_backlog_caution')

    if overdue_count >= 6 or high_priority_count >= 10 or (stale_blocked_count >= 4 and overdue_count >= 4):
        return GovernanceBacklogPressureState.CRITICAL, reason_codes
    if overdue_count >= 4 or high_priority_count >= 7 or stale_blocked_count >= 2 or (overdue_count >= 3 and stale_blocked_count >= 2):
        return GovernanceBacklogPressureState.HIGH, reason_codes
    if overdue_count >= 2 or high_priority_count >= 4 or active_count >= 12 or followup_due_count >= 5:
        return GovernanceBacklogPressureState.CAUTION, reason_codes
    return GovernanceBacklogPressureState.NORMAL, reason_codes


def build_backlog_pressure_snapshot(*, pressure_run: GovernanceBacklogPressureRun | None = None) -> GovernanceBacklogPressureSnapshot:
    active_items = list(
        GovernanceReviewItem.objects.filter(item_status__in=[GovernanceReviewItemStatus.OPEN, GovernanceReviewItemStatus.IN_REVIEW])
    )

    open_count = sum(1 for item in active_items if item.item_status == GovernanceReviewItemStatus.OPEN)
    in_review_count = sum(1 for item in active_items if item.item_status == GovernanceReviewItemStatus.IN_REVIEW)
    p1_count = sum(1 for item in active_items if item.queue_priority == GovernanceReviewPriority.P1)
    p2_count = sum(1 for item in active_items if item.queue_priority == GovernanceReviewPriority.P2)
    overdue_count = sum(1 for item in active_items if _is_overdue(item))
    stale_blocked_count = sum(1 for item in active_items if _is_stale_blocked(item))
    followup_due_count = sum(1 for item in active_items if _is_followup_due(item))

    pressure_state, reason_codes = _derive_pressure_state(
        open_count=open_count,
        in_review_count=in_review_count,
        p1_count=p1_count,
        p2_count=p2_count,
        overdue_count=overdue_count,
        stale_blocked_count=stale_blocked_count,
        followup_due_count=followup_due_count,
    )

    summary = (
        f'Backlog pressure={pressure_state} (open={open_count}, in_review={in_review_count}, '
        f'P1={p1_count}, P2={p2_count}, overdue={overdue_count}, stale_blocked={stale_blocked_count}, '
        f'followup_due={followup_due_count}).'
    )

    return GovernanceBacklogPressureSnapshot.objects.create(
        linked_pressure_run=pressure_run,
        open_item_count=open_count,
        in_review_count=in_review_count,
        p1_count=p1_count,
        p2_count=p2_count,
        overdue_count=overdue_count,
        stale_blocked_count=stale_blocked_count,
        followup_due_count=followup_due_count,
        pressure_state=pressure_state,
        snapshot_summary=summary,
        reason_codes=reason_codes,
        metadata={
            'considered_item_ids': [item.id for item in active_items],
            'considered_item_count': len(active_items),
        },
    )

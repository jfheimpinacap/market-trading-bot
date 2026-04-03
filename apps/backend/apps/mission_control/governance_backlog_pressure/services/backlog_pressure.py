from __future__ import annotations

from dataclasses import dataclass

from apps.mission_control.models import (
    GovernanceBacklogPressureState,
    GovernanceQueueAgeBucket,
    GovernanceQueueAgingReview,
    GovernanceReviewItem,
    GovernanceReviewItemStatus,
    GovernanceReviewPriority,
)
from apps.runtime_governor.tuning_profiles import get_runtime_conservative_tuning_profile


@dataclass
class BacklogPressureAssessment:
    open_item_count: int
    overdue_count: int
    overdue_p1_count: int
    followup_due_count: int
    stale_blocked_count: int
    persistent_stale_blocked_count: int
    pressure_score: int
    governance_backlog_pressure_state: str
    snapshot_summary: str
    reason_codes: list[str]
    metadata: dict


def _is_persistent_stale_blocked(*, item_id: int) -> bool:
    latest_reviews = list(
        GovernanceQueueAgingReview.objects.filter(linked_review_item_id=item_id)
        .order_by('-created_at', '-id')[:2]
    )
    return len(latest_reviews) == 2 and all(review.aging_status == 'STALE_BLOCKED' for review in latest_reviews)


def assess_backlog_pressure() -> BacklogPressureAssessment:
    tuning = get_runtime_conservative_tuning_profile()
    open_items = GovernanceReviewItem.objects.filter(
        item_status__in=[GovernanceReviewItemStatus.OPEN, GovernanceReviewItemStatus.IN_REVIEW],
    )

    overdue_items = open_items.filter(
        id__in=list(
            GovernanceQueueAgingReview.objects.filter(age_bucket=GovernanceQueueAgeBucket.OVERDUE).values_list(
                'linked_review_item_id',
                flat=True,
            )
        )
    )

    overdue_p1_count = overdue_items.filter(queue_priority=GovernanceReviewPriority.P1).count()
    stale_blocked_reviews = GovernanceQueueAgingReview.objects.filter(
        linked_review_item__in=open_items,
        aging_status='STALE_BLOCKED',
    )
    followup_due_count = GovernanceQueueAgingReview.objects.filter(
        linked_review_item__in=open_items,
        aging_status='FOLLOWUP_DUE',
    ).values('linked_review_item_id').distinct().count()
    stale_blocked_item_ids = set(stale_blocked_reviews.values_list('linked_review_item_id', flat=True))
    persistent_stale_blocked_count = sum(1 for item_id in stale_blocked_item_ids if _is_persistent_stale_blocked(item_id=item_id))

    overdue_count = overdue_items.count()
    stale_blocked_count = len(stale_blocked_item_ids)
    pressure_score = (
        (overdue_count * tuning.overdue_weight)
        + (overdue_p1_count * tuning.overdue_p1_weight)
        + (stale_blocked_count * tuning.stale_blocked_weight)
        + (persistent_stale_blocked_count * tuning.persistent_stale_blocked_weight)
        + (followup_due_count * tuning.followup_due_weight)
    )

    if overdue_p1_count >= 2 or overdue_count >= 6 or persistent_stale_blocked_count >= 2 or pressure_score >= tuning.backlog_high_threshold:
        state = GovernanceBacklogPressureState.HIGH
    elif overdue_p1_count >= 1 or overdue_count >= 2 or stale_blocked_count >= 1 or pressure_score >= tuning.backlog_caution_threshold:
        state = GovernanceBacklogPressureState.CAUTION
    else:
        state = GovernanceBacklogPressureState.NORMAL

    reason_codes: list[str] = []
    if overdue_count:
        reason_codes.append(f'OVERDUE_ITEMS:{overdue_count}')
    if overdue_p1_count:
        reason_codes.append(f'OVERDUE_P1:{overdue_p1_count}')
    if followup_due_count:
        reason_codes.append(f'FOLLOWUP_DUE:{followup_due_count}')
    if stale_blocked_count:
        reason_codes.append(f'STALE_BLOCKED:{stale_blocked_count}')
    if persistent_stale_blocked_count:
        reason_codes.append(f'PERSISTENT_STALE_BLOCKED:{persistent_stale_blocked_count}')
    if not reason_codes:
        reason_codes.append('BACKLOG_WITHIN_BOUNDS')

    summary = (
        f'Backlog pressure={state} with open={open_items.count()}, overdue={overdue_count}, '
        f'overdue_p1={overdue_p1_count}, stale_blocked={stale_blocked_count}, '
        f'persistent_stale_blocked={persistent_stale_blocked_count}.'
    )

    return BacklogPressureAssessment(
        open_item_count=open_items.count(),
        overdue_count=overdue_count,
        overdue_p1_count=overdue_p1_count,
        followup_due_count=followup_due_count,
        stale_blocked_count=stale_blocked_count,
        persistent_stale_blocked_count=persistent_stale_blocked_count,
        pressure_score=pressure_score,
        governance_backlog_pressure_state=state,
        snapshot_summary=summary,
        reason_codes=reason_codes,
        metadata={
            'tuning_profile': tuning.profile_name,
            'thresholds': {
                'caution': tuning.backlog_caution_threshold,
                'high': tuning.backlog_high_threshold,
                'critical': tuning.backlog_critical_threshold,
            },
            'weights': {
                'overdue': tuning.overdue_weight,
                'overdue_p1': tuning.overdue_p1_weight,
                'stale_blocked': tuning.stale_blocked_weight,
                'persistent_stale_blocked': tuning.persistent_stale_blocked_weight,
                'followup_due': tuning.followup_due_weight,
            },
        },
    )

from __future__ import annotations

from dataclasses import dataclass

from django.utils.dateparse import parse_datetime
from django.utils import timezone

from apps.mission_control.models import (
    GovernanceQueueAgeBucket,
    GovernanceQueueAgingStatus,
    GovernanceReviewItem,
    GovernanceReviewItemStatus,
)


@dataclass
class AgingAssessment:
    age_bucket: str
    aging_status: str
    review_summary: str
    reason_codes: list[str]
    metadata: dict


OPEN_AGING_DAYS = 3
OPEN_STALE_DAYS = 7
OPEN_OVERDUE_DAYS = 14
IN_REVIEW_OVERDUE_DAYS = 5
BLOCKED_STALE_DAYS = 4
FOLLOWUP_DUE_GRACE_DAYS = 3


def _age_bucket(age_days: int) -> str:
    if age_days >= OPEN_OVERDUE_DAYS:
        return GovernanceQueueAgeBucket.OVERDUE
    if age_days >= OPEN_STALE_DAYS:
        return GovernanceQueueAgeBucket.STALE
    if age_days >= OPEN_AGING_DAYS:
        return GovernanceQueueAgeBucket.AGING
    return GovernanceQueueAgeBucket.FRESH


def assess_item_aging(*, item: GovernanceReviewItem, as_of=None) -> AgingAssessment:
    as_of = as_of or timezone.now()
    age_days = max(0, (as_of - item.created_at).days)
    stale_days = max(0, (as_of - item.updated_at).days)
    blockers = [*item.blockers, *item.reason_codes]

    followup_required = bool(item.metadata.get('followup_required')) or any('FOLLOWUP' in marker for marker in blockers)
    followup_due_at = item.metadata.get('followup_due_at') or item.metadata.get('next_review_at')
    followup_due = False
    if followup_due_at:
        parsed_followup_due_at = parse_datetime(str(followup_due_at))
        if parsed_followup_due_at:
            if timezone.is_naive(parsed_followup_due_at):
                parsed_followup_due_at = timezone.make_aware(parsed_followup_due_at, timezone.get_current_timezone())
            followup_due = parsed_followup_due_at <= as_of
    elif followup_required and stale_days >= FOLLOWUP_DUE_GRACE_DAYS:
        followup_due = True

    if item.item_status == GovernanceReviewItemStatus.IN_REVIEW and stale_days >= IN_REVIEW_OVERDUE_DAYS:
        return AgingAssessment(
            age_bucket=GovernanceQueueAgeBucket.OVERDUE,
            aging_status=GovernanceQueueAgingStatus.MANUAL_REVIEW_OVERDUE,
            review_summary='Item has been in manual review too long without an update.',
            reason_codes=['IN_REVIEW_STALLED', 'MANUAL_REVIEW_OVERDUE'],
            metadata={'age_days': age_days, 'stale_days': stale_days},
        )

    if any('BLOCKED' in marker for marker in blockers) and stale_days >= BLOCKED_STALE_DAYS:
        return AgingAssessment(
            age_bucket=_age_bucket(age_days),
            aging_status=GovernanceQueueAgingStatus.STALE_BLOCKED,
            review_summary='Blocked governance item remains stale and should be escalated.',
            reason_codes=['BLOCKED_PERSISTENT', 'STALE_BLOCKED'],
            metadata={'age_days': age_days, 'stale_days': stale_days},
        )

    if followup_due:
        return AgingAssessment(
            age_bucket=_age_bucket(age_days),
            aging_status=GovernanceQueueAgingStatus.FOLLOWUP_DUE,
            review_summary='Follow-up window has elapsed and requires immediate review.',
            reason_codes=['FOLLOWUP_DUE_NOW'],
            metadata={'age_days': age_days, 'stale_days': stale_days, 'followup_due': True},
        )

    if item.item_status == GovernanceReviewItemStatus.OPEN and age_days >= OPEN_STALE_DAYS:
        return AgingAssessment(
            age_bucket=_age_bucket(age_days),
            aging_status=GovernanceQueueAgingStatus.PRIORITY_ESCALATION,
            review_summary='Open governance item has aged and should increase queue priority.',
            reason_codes=['OPEN_ITEM_AGED'],
            metadata={'age_days': age_days, 'stale_days': stale_days},
        )

    return AgingAssessment(
        age_bucket=_age_bucket(age_days),
        aging_status=GovernanceQueueAgingStatus.NORMAL,
        review_summary='Item age is within expected review window.',
        reason_codes=['AGE_WITHIN_WINDOW'],
        metadata={'age_days': age_days, 'stale_days': stale_days},
    )

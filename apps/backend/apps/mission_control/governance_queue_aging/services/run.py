from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.mission_control.governance_queue_aging.services.aging import assess_item_aging
from apps.mission_control.governance_queue_aging.services.escalation import build_escalation_decision
from apps.mission_control.models import (
    GovernanceQueueAgeBucket,
    GovernanceQueueAgingRecommendation,
    GovernanceQueueAgingRecommendationType,
    GovernanceQueueAgingRun,
    GovernanceQueueAgingReview,
    GovernanceQueueAgingStatus,
    GovernanceReviewItem,
    GovernanceReviewItemStatus,
)


def run_governance_queue_aging_review() -> GovernanceQueueAgingRun:
    run = GovernanceQueueAgingRun.objects.create(started_at=timezone.now())
    open_items = list(
        GovernanceReviewItem.objects.filter(
            item_status__in=[GovernanceReviewItemStatus.OPEN, GovernanceReviewItemStatus.IN_REVIEW],
        ).order_by('queue_priority', '-updated_at', '-id')
    )

    with transaction.atomic():
        for item in open_items:
            assessment = assess_item_aging(item=item)
            review = GovernanceQueueAgingReview.objects.create(
                linked_review_item=item,
                linked_aging_run=run,
                age_bucket=assessment.age_bucket,
                aging_status=assessment.aging_status,
                review_summary=assessment.review_summary,
                reason_codes=assessment.reason_codes,
                metadata=assessment.metadata,
            )
            decision = build_escalation_decision(item=item, aging_status=assessment.aging_status)
            GovernanceQueueAgingRecommendation.objects.create(
                linked_review_item=item,
                linked_aging_review=review,
                recommendation_type=decision.recommendation_type,
                rationale=decision.rationale,
                confidence=decision.confidence,
                blockers=decision.blockers,
            )

            if decision.suggested_priority != item.queue_priority:
                item.queue_priority = decision.suggested_priority
                item.save(update_fields=['queue_priority', 'updated_at'])

        run.considered_item_count = len(open_items)
        run.stale_item_count = sum(
            1
            for review in run.reviews.all()
            if review.age_bucket in {GovernanceQueueAgeBucket.STALE, GovernanceQueueAgeBucket.OVERDUE}
        )
        run.escalated_count = GovernanceQueueAgingRecommendation.objects.filter(
            linked_aging_review__linked_aging_run=run,
        ).exclude(recommendation_type=GovernanceQueueAgingRecommendationType.KEEP_PRIORITY).count()
        run.followup_due_count = run.reviews.filter(aging_status=GovernanceQueueAgingStatus.FOLLOWUP_DUE).count()
        run.blocked_stale_count = run.reviews.filter(aging_status=GovernanceQueueAgingStatus.STALE_BLOCKED).count()
        run.metadata = {
            'overdue_count': run.reviews.filter(age_bucket=GovernanceQueueAgeBucket.OVERDUE).count(),
            'manual_review_overdue_count': run.reviews.filter(aging_status=GovernanceQueueAgingStatus.MANUAL_REVIEW_OVERDUE).count(),
        }
        run.completed_at = timezone.now()
        run.save()

    return run


def governance_queue_aging_summary() -> dict:
    latest_run = GovernanceQueueAgingRun.objects.order_by('-started_at', '-id').first()
    latest_reviews = GovernanceQueueAgingReview.objects.select_related('linked_review_item').order_by('-created_at', '-id')[:200]

    return {
        'latest_run_id': latest_run.id if latest_run else None,
        'latest_counts': {
            'considered': latest_run.considered_item_count if latest_run else 0,
            'stale_items': latest_run.stale_item_count if latest_run else 0,
            'escalated': latest_run.escalated_count if latest_run else 0,
            'followup_due': latest_run.followup_due_count if latest_run else 0,
            'blocked_stale': latest_run.blocked_stale_count if latest_run else 0,
            'overdue': latest_run.metadata.get('overdue_count', 0) if latest_run else 0,
            'manual_review_overdue': latest_run.metadata.get('manual_review_overdue_count', 0) if latest_run else 0,
        },
        'totals': {
            'runs': GovernanceQueueAgingRun.objects.count(),
            'reviews': GovernanceQueueAgingReview.objects.count(),
            'recommendations': GovernanceQueueAgingRecommendation.objects.count(),
        },
        'status_breakdown': {
            'priority_escalation': sum(1 for review in latest_reviews if review.aging_status == GovernanceQueueAgingStatus.PRIORITY_ESCALATION),
            'followup_due': sum(1 for review in latest_reviews if review.aging_status == GovernanceQueueAgingStatus.FOLLOWUP_DUE),
            'stale_blocked': sum(1 for review in latest_reviews if review.aging_status == GovernanceQueueAgingStatus.STALE_BLOCKED),
            'manual_review_overdue': sum(1 for review in latest_reviews if review.aging_status == GovernanceQueueAgingStatus.MANUAL_REVIEW_OVERDUE),
        },
    }

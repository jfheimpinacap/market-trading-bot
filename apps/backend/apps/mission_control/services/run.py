from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.mission_control.models import (
    GovernanceReviewItem,
    GovernanceReviewItemStatus,
    GovernanceReviewPriority,
    GovernanceReviewQueueRun,
    GovernanceReviewRecommendation,
    GovernanceReviewSeverity,
)
from apps.mission_control.services.collect import collect_governance_review_candidates
from apps.mission_control.services.prioritize import assign_severity_and_priority
from apps.mission_control.services.recommendation import build_recommendation_for_item


def run_governance_review_queue() -> GovernanceReviewQueueRun:
    run = GovernanceReviewQueueRun.objects.create(started_at=timezone.now())
    candidates = collect_governance_review_candidates()

    with transaction.atomic():
        touched_item_ids: list[int] = []
        for candidate in candidates:
            severity, priority = assign_severity_and_priority(candidate)
            item, _created = GovernanceReviewItem.objects.get_or_create(
                source_module=candidate.source_module,
                source_type=candidate.source_type,
                source_object_id=candidate.source_object_id,
                defaults={
                    'item_status': GovernanceReviewItemStatus.OPEN,
                    'severity': severity,
                    'queue_priority': priority,
                    'linked_session_id': candidate.linked_session_id,
                    'linked_market_id': candidate.linked_market_id,
                    'title': candidate.title,
                    'summary': candidate.summary,
                    'blockers': candidate.blockers,
                    'reason_codes': candidate.reason_codes,
                    'metadata': candidate.metadata,
                },
            )

            incoming_signature = {
                'severity': severity,
                'queue_priority': priority,
                'title': candidate.title,
                'summary': candidate.summary,
                'blockers': candidate.blockers,
                'reason_codes': candidate.reason_codes,
                'metadata': candidate.metadata,
                'linked_session_id': candidate.linked_session_id,
                'linked_market_id': candidate.linked_market_id,
            }
            stored_signature = {
                'severity': item.severity,
                'queue_priority': item.queue_priority,
                'title': item.title,
                'summary': item.summary,
                'blockers': item.blockers,
                'reason_codes': item.reason_codes,
                'metadata': item.metadata,
                'linked_session_id': item.linked_session_id,
                'linked_market_id': item.linked_market_id,
            }
            has_real_change = incoming_signature != stored_signature

            if item.item_status in {GovernanceReviewItemStatus.RESOLVED, GovernanceReviewItemStatus.DISMISSED} and has_real_change:
                item.item_status = GovernanceReviewItemStatus.OPEN

            if has_real_change:
                item.severity = severity
                item.queue_priority = priority
                item.title = candidate.title
                item.summary = candidate.summary
                item.blockers = candidate.blockers
                item.reason_codes = candidate.reason_codes
                item.metadata = candidate.metadata
                item.linked_session_id = candidate.linked_session_id
                item.linked_market_id = candidate.linked_market_id
                item.save()

            touched_item_ids.append(item.id)
            GovernanceReviewRecommendation.objects.filter(linked_review_item=item).delete()
            build_recommendation_for_item(item)

        open_items = GovernanceReviewItem.objects.filter(
            item_status__in=[GovernanceReviewItemStatus.OPEN, GovernanceReviewItemStatus.IN_REVIEW],
        )

        run.collected_item_count = len(touched_item_ids)
        open_items_list = list(open_items)
        run.high_priority_count = sum(1 for item in open_items_list if item.queue_priority == GovernanceReviewPriority.P1)
        run.blocked_count = sum(
            1 for item in open_items_list
            if 'STATUS_BLOCKED' in [*item.blockers, *item.reason_codes]
        )
        run.deferred_count = sum(
            1 for item in open_items_list
            if any('DEFER' in marker for marker in [*item.blockers, *item.reason_codes])
        )
        run.manual_review_count = sum(
            1 for item in open_items_list
            if any('MANUAL' in marker for marker in item.reason_codes)
        )
        run.metadata = {
            'touched_item_ids': touched_item_ids,
            'critical_count': sum(1 for item in open_items_list if item.severity == GovernanceReviewSeverity.CRITICAL),
            'high_count': sum(1 for item in open_items_list if item.severity == GovernanceReviewSeverity.HIGH),
        }
        run.completed_at = timezone.now()
        run.save()

    return run


def governance_review_summary() -> dict:
    open_items = GovernanceReviewItem.objects.filter(
        item_status__in=[GovernanceReviewItemStatus.OPEN, GovernanceReviewItemStatus.IN_REVIEW],
    )
    latest_run = GovernanceReviewQueueRun.objects.order_by('-started_at', '-id').first()
    open_items_list = list(open_items)
    by_source_module: dict[str, int] = {}
    for item in open_items_list:
        by_source_module[item.source_module] = by_source_module.get(item.source_module, 0) + 1

    return {
        'latest_run': latest_run.id if latest_run else None,
        'open_count': len(open_items_list),
        'resolved_count': GovernanceReviewItem.objects.filter(item_status=GovernanceReviewItemStatus.RESOLVED).count(),
        'high_priority_count': sum(1 for item in open_items_list if item.queue_priority == GovernanceReviewPriority.P1),
        'blocked_count': sum(1 for item in open_items_list if 'STATUS_BLOCKED' in [*item.blockers, *item.reason_codes]),
        'deferred_count': sum(1 for item in open_items_list if any('DEFER' in marker for marker in [*item.blockers, *item.reason_codes])),
        'manual_review_count': sum(1 for item in open_items_list if any('MANUAL' in marker for marker in item.reason_codes)),
        'by_source_module': by_source_module,
    }

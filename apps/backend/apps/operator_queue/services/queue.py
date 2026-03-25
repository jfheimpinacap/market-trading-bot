from datetime import timedelta
from django.db.models import Count, Q
from django.utils import timezone

from apps.operator_queue.models import OperatorQueueItem, OperatorQueuePriority, OperatorQueueStatus


def get_queue_queryset():
    now = timezone.now()
    return OperatorQueueItem.objects.select_related(
        'related_proposal',
        'related_market',
        'related_pending_approval',
        'related_trade',
    ).exclude(status=OperatorQueueStatus.SNOOZED, snoozed_until__gt=now)


def build_queue_summary() -> dict:
    now = timezone.now()
    day_ago = now - timedelta(days=1)
    return {
        'pending_count': OperatorQueueItem.objects.filter(status=OperatorQueueStatus.PENDING).count(),
        'high_priority_count': OperatorQueueItem.objects.filter(priority__in=[OperatorQueuePriority.HIGH, OperatorQueuePriority.CRITICAL], status=OperatorQueueStatus.PENDING).count(),
        'approvals_recent': OperatorQueueItem.objects.filter(status__in=[OperatorQueueStatus.APPROVED, OperatorQueueStatus.EXECUTED], updated_at__gte=day_ago).count(),
        'rejected_recent': OperatorQueueItem.objects.filter(status=OperatorQueueStatus.REJECTED, updated_at__gte=day_ago).count(),
        'snoozed_count': OperatorQueueItem.objects.filter(status=OperatorQueueStatus.SNOOZED, snoozed_until__gte=now).count(),
        'decision_breakdown': list(
            OperatorQueueItem.objects.values('status').annotate(count=Count('id')).order_by('status')
        ),
        'logs_recent': list(
            OperatorQueueItem.objects.filter(decision_logs__created_at__gte=day_ago)
            .values('decision_logs__decision')
            .annotate(count=Count('decision_logs__id'))
            .order_by('decision_logs__decision')
        ),
        'paper_demo_only': True,
        'real_execution_enabled': False,
        'manual_operator_required_for_exceptions': True,
    }

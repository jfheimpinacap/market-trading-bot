from datetime import timedelta

from django.db.models import Count
from django.utils import timezone

from apps.operator_alerts.models import OperatorAlert, OperatorAlertStatus, OperatorDigest
from apps.operator_queue.models import OperatorQueueItem, OperatorQueuePriority, OperatorQueueStatus
from apps.runtime_governor.models import RuntimeTransitionLog
from apps.safety_guard.models import SafetyEvent


def build_digest(*, digest_type: str = 'session', window_start=None, window_end=None) -> OperatorDigest:
    end = window_end or timezone.now()
    start = window_start or (end - timedelta(hours=24))

    alerts_qs = OperatorAlert.objects.filter(created_at__gte=start, created_at__lte=end)
    critical_count = alerts_qs.filter(severity='critical').count()
    approvals_pending_count = OperatorQueueItem.objects.filter(status=OperatorQueueStatus.PENDING, priority__in=[OperatorQueuePriority.HIGH, OperatorQueuePriority.CRITICAL]).count()
    safety_events_count = SafetyEvent.objects.filter(created_at__gte=start, created_at__lte=end).count()
    runtime_changes_count = RuntimeTransitionLog.objects.filter(created_at__gte=start, created_at__lte=end).count()

    top_sources = list(
        alerts_qs.values('source').annotate(count=Count('id')).order_by('-count', 'source')[:5]
    )

    summary = (
        f'Window generated {alerts_qs.count()} alerts ({critical_count} critical). '
        f'Pending high-priority approvals: {approvals_pending_count}. '
        f'Safety events: {safety_events_count}. Runtime changes: {runtime_changes_count}.'
    )

    return OperatorDigest.objects.create(
        digest_type=digest_type,
        window_start=start,
        window_end=end,
        summary=summary,
        alerts_count=alerts_qs.count(),
        critical_count=critical_count,
        approvals_pending_count=approvals_pending_count,
        safety_events_count=safety_events_count,
        runtime_changes_count=runtime_changes_count,
        metadata={'top_sources': top_sources},
    )

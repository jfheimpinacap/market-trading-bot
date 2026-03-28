from django.db.models import Count
from datetime import timedelta

from django.utils import timezone

from apps.approval_center.models import ApprovalPriority, ApprovalRequest, ApprovalRequestStatus
from apps.approval_center.services.requests import sync_approval_requests


def get_approval_queue_summary() -> dict:
    sync_approval_requests()
    base = ApprovalRequest.objects.all()
    counts_by_status = {row['status']: row['total'] for row in base.values('status').annotate(total=Count('id'))}
    high_priority_pending = base.filter(status=ApprovalRequestStatus.PENDING, priority__in=[ApprovalPriority.HIGH, ApprovalPriority.CRITICAL]).count()
    approved_recently = base.filter(status=ApprovalRequestStatus.APPROVED, decided_at__gte=timezone.now() - timedelta(hours=24)).count()
    expired_or_escalated = base.filter(status__in=[ApprovalRequestStatus.EXPIRED, ApprovalRequestStatus.ESCALATED]).count()

    return {
        'pending': counts_by_status.get(ApprovalRequestStatus.PENDING, 0),
        'approved': counts_by_status.get(ApprovalRequestStatus.APPROVED, 0),
        'rejected': counts_by_status.get(ApprovalRequestStatus.REJECTED, 0),
        'expired': counts_by_status.get(ApprovalRequestStatus.EXPIRED, 0),
        'escalated': counts_by_status.get(ApprovalRequestStatus.ESCALATED, 0),
        'cancelled': counts_by_status.get(ApprovalRequestStatus.CANCELLED, 0),
        'high_priority_pending': high_priority_pending,
        'approved_recently': approved_recently,
        'expired_or_escalated': expired_or_escalated,
        'top_high_priority': [
            {
                'id': item.id,
                'source_type': item.source_type,
                'title': item.title,
                'priority': item.priority,
                'requested_at': item.requested_at,
            }
            for item in base.filter(status=ApprovalRequestStatus.PENDING, priority__in=[ApprovalPriority.HIGH, ApprovalPriority.CRITICAL]).order_by('-requested_at')[:5]
        ],
    }

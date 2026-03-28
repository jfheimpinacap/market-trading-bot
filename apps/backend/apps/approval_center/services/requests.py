from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.approval_center.models import ApprovalRequest, ApprovalRequestStatus
from apps.approval_center.services.impact import get_approval_impact_preview
from apps.approval_center.services.sources import collect_approval_source_records


@transaction.atomic
def sync_approval_requests() -> int:
    source_records = collect_approval_source_records()
    synced = 0
    for record in source_records:
        defaults = {
            'title': record.title,
            'summary': record.summary,
            'priority': record.priority,
            'status': record.status,
            'requested_at': record.requested_at,
            'expires_at': record.expires_at,
            'metadata': record.metadata,
            'decided_at': timezone.now() if record.status != ApprovalRequestStatus.PENDING else None,
        }
        obj, created = ApprovalRequest.objects.update_or_create(
            source_type=record.source_type,
            source_object_id=record.source_object_id,
            defaults=defaults,
        )
        if not created and record.status == ApprovalRequestStatus.PENDING and obj.decided_at is not None:
            obj.decided_at = None
            obj.save(update_fields=['decided_at', 'updated_at'])
        synced += 1
    return synced


def list_approvals(*, status: str | None = None, only_pending: bool = False):
    sync_approval_requests()
    queryset = ApprovalRequest.objects.prefetch_related('decisions').order_by('-requested_at', '-id')
    if only_pending:
        queryset = queryset.filter(status=ApprovalRequestStatus.PENDING)
    elif status:
        queryset = queryset.filter(status=status.upper())
    return queryset[:200]


def get_approval_detail(approval_id: int) -> ApprovalRequest:
    sync_approval_requests()
    approval = ApprovalRequest.objects.prefetch_related('decisions').get(pk=approval_id)
    approval.metadata = {
        **(approval.metadata or {}),
        'impact_preview': get_approval_impact_preview(approval),
    }
    return approval

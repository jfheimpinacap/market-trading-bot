from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from apps.operator_alerts.models import OperatorAlert, OperatorAlertStatus


@dataclass
class AlertEmitPayload:
    alert_type: str
    severity: str
    title: str
    summary: str
    source: str
    dedupe_key: str | None = None
    related_object_type: str | None = None
    related_object_id: str | None = None
    metadata: dict | None = None


def emit_alert(payload: AlertEmitPayload) -> OperatorAlert:
    now = timezone.now()
    metadata = payload.metadata or {}

    if payload.dedupe_key:
        existing = OperatorAlert.objects.filter(dedupe_key=payload.dedupe_key).exclude(status=OperatorAlertStatus.RESOLVED).first()
        if existing:
            existing.severity = payload.severity
            existing.title = payload.title
            existing.summary = payload.summary
            existing.source = payload.source
            existing.last_seen_at = now
            existing.related_object_type = payload.related_object_type
            existing.related_object_id = payload.related_object_id
            existing.metadata = {**existing.metadata, **metadata}
            if existing.status == OperatorAlertStatus.SUPPRESSED:
                existing.status = OperatorAlertStatus.OPEN
            existing.save(update_fields=[
                'severity', 'title', 'summary', 'source', 'last_seen_at', 'related_object_type', 'related_object_id', 'metadata', 'status', 'updated_at'
            ])
            return existing

    return OperatorAlert.objects.create(
        alert_type=payload.alert_type,
        severity=payload.severity,
        status=OperatorAlertStatus.OPEN,
        title=payload.title,
        summary=payload.summary,
        source=payload.source,
        related_object_type=payload.related_object_type,
        related_object_id=payload.related_object_id,
        dedupe_key=payload.dedupe_key,
        first_seen_at=now,
        last_seen_at=now,
        metadata=metadata,
    )


def acknowledge_alert(alert: OperatorAlert) -> OperatorAlert:
    alert.status = OperatorAlertStatus.ACKNOWLEDGED
    alert.save(update_fields=['status', 'updated_at'])
    return alert


def resolve_alert(alert: OperatorAlert) -> OperatorAlert:
    alert.status = OperatorAlertStatus.RESOLVED
    alert.save(update_fields=['status', 'updated_at'])
    return alert


def get_alerts_summary() -> dict:
    open_qs = OperatorAlert.objects.filter(status__in=[OperatorAlertStatus.OPEN, OperatorAlertStatus.ACKNOWLEDGED])
    return {
        'open_alerts': open_qs.count(),
        'critical_alerts': open_qs.filter(severity='critical').count(),
        'warning_alerts': open_qs.filter(severity='warning').count(),
        'high_alerts': open_qs.filter(severity='high').count(),
        'pending_approvals_attention': open_qs.filter(alert_type='approval_required').count(),
        'stale_provider_issues': open_qs.filter(alert_type='sync', dedupe_key__icontains='stale').count(),
        'by_source': list(open_qs.values('source').annotate(count=Count('id')).order_by('source')),
    }


@transaction.atomic
def rebuild_operator_alerts() -> dict:
    from apps.operator_alerts.services.aggregation import run_default_alert_aggregation

    created = run_default_alert_aggregation()
    return {'created_or_refreshed': created}

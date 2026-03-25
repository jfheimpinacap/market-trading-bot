from datetime import timedelta

from django.db.models import Count
from django.utils import timezone

from apps.notification_center.models import (
    NotificationDeliveryMode,
    NotificationEscalationEvent,
    NotificationTriggerSource,
)
from apps.notification_center.services.automation import get_or_create_automation_state
from apps.notification_center.services.delivery import send_alert_notifications
from apps.operator_alerts.models import OperatorAlert, OperatorAlertSeverity, OperatorAlertStatus


def run_escalation_cycle(*, force: bool = False) -> dict:
    state = get_or_create_automation_state()
    if not state.is_enabled or not state.escalation_enabled:
        return {'enabled': False, 'escalations': 0, 'deliveries': 0}

    now = timezone.now()
    cutoff = now - timedelta(minutes=state.escalation_after_minutes)
    open_alerts = OperatorAlert.objects.filter(
        status__in=[OperatorAlertStatus.OPEN, OperatorAlertStatus.ACKNOWLEDGED],
        last_seen_at__lte=cutoff,
    ).order_by('-severity', '-last_seen_at')

    escalations = 0
    deliveries = 0
    for alert in open_alerts[:30]:
        if alert.severity not in {OperatorAlertSeverity.CRITICAL, OperatorAlertSeverity.HIGH, OperatorAlertSeverity.WARNING}:
            continue

        reason = f'alert_open_for_{state.escalation_after_minutes}_minutes'
        if alert.severity == OperatorAlertSeverity.WARNING:
            repeated = OperatorAlert.objects.filter(
                dedupe_key=alert.dedupe_key,
                severity=OperatorAlertSeverity.WARNING,
                status__in=[OperatorAlertStatus.OPEN, OperatorAlertStatus.ACKNOWLEDGED],
            ).aggregate(total=Count('id'))['total'] or 0
            if repeated < 3 and not force:
                continue
            reason = f'warning_repeated_{repeated}_times'

        if NotificationEscalationEvent.objects.filter(alert=alert, reason=reason, created_at__gte=cutoff).exists() and not force:
            continue

        NotificationEscalationEvent.objects.create(
            alert=alert,
            severity=alert.severity,
            reason=reason,
            status='TRIGGERED',
            metadata={'source': alert.source, 'alert_type': alert.alert_type},
        )
        escalation_deliveries = send_alert_notifications(
            alert,
            force=True,
            trigger_source=NotificationTriggerSource.ESCALATION,
            mode=NotificationDeliveryMode.ESCALATION,
            allowed_rule_modes=(
                NotificationDeliveryMode.ESCALATION,
                NotificationDeliveryMode.ESCALATION_ONLY,
                NotificationDeliveryMode.IMMEDIATE,
            ),
        )
        escalations += 1
        deliveries += len(escalation_deliveries)

    state.last_escalation_cycle_at = now
    state.save(update_fields=['last_escalation_cycle_at', 'updated_at'])
    return {'enabled': True, 'escalations': escalations, 'deliveries': deliveries}

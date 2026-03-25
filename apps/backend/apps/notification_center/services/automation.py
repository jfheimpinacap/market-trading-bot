from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.notification_center.models import (
    NotificationAutomationState,
    NotificationDelivery,
    NotificationDeliveryMode,
    NotificationTriggerSource,
)
from apps.notification_center.services.delivery import send_alert_notifications
from apps.operator_alerts.models import OperatorAlert, OperatorAlertSeverity, OperatorAlertStatus

AUTOMATIC_SOURCES = {'runtime', 'safety', 'continuous_demo', 'operator_queue', 'readiness'}


def get_or_create_automation_state() -> NotificationAutomationState:
    state, _ = NotificationAutomationState.objects.get_or_create(id=1)
    return state


def set_automation_enabled(enabled: bool) -> NotificationAutomationState:
    state = get_or_create_automation_state()
    state.is_enabled = enabled
    state.save(update_fields=['is_enabled', 'updated_at'])
    return state


def _within_rate_limit(state: NotificationAutomationState) -> bool:
    since = timezone.now() - timedelta(minutes=state.automation_window_minutes)
    sent_count = NotificationDelivery.objects.filter(
        trigger_source=NotificationTriggerSource.AUTOMATIC,
        created_at__gte=since,
        delivery_mode=NotificationDeliveryMode.IMMEDIATE,
    ).count()
    return sent_count < state.max_auto_notifications_per_window


def _alert_relevant_for_automation(alert: OperatorAlert, state: NotificationAutomationState) -> bool:
    if alert.status not in {OperatorAlertStatus.OPEN, OperatorAlertStatus.ACKNOWLEDGED}:
        return False
    if state.suppress_info_alerts_by_default and alert.severity == OperatorAlertSeverity.INFO:
        return False
    return alert.severity == OperatorAlertSeverity.CRITICAL or alert.source in AUTOMATIC_SOURCES


@transaction.atomic
def run_automatic_dispatch(*, alert_ids: list[int] | None = None, limit: int = 25) -> dict:
    state = get_or_create_automation_state()
    if not state.is_enabled or not state.automatic_dispatch_enabled:
        return {'enabled': False, 'processed': 0, 'deliveries': 0}

    queryset = OperatorAlert.objects.filter(status__in=[OperatorAlertStatus.OPEN, OperatorAlertStatus.ACKNOWLEDGED]).order_by('-last_seen_at', '-id')
    if alert_ids:
        queryset = queryset.filter(id__in=alert_ids)

    processed = 0
    deliveries_total = 0
    for alert in queryset[:limit]:
        if not _alert_relevant_for_automation(alert, state):
            continue
        if not _within_rate_limit(state):
            break
        deliveries = send_alert_notifications(
            alert,
            trigger_source=NotificationTriggerSource.AUTOMATIC,
            allowed_rule_modes=(NotificationDeliveryMode.IMMEDIATE,),
        )
        processed += 1
        deliveries_total += len(deliveries)

    if processed > 0:
        state.last_automatic_dispatch_at = timezone.now()
        state.save(update_fields=['last_automatic_dispatch_at', 'updated_at'])

    return {'enabled': True, 'processed': processed, 'deliveries': deliveries_total}


def run_automatic_dispatch_for_alert(alert: OperatorAlert) -> dict:
    return run_automatic_dispatch(alert_ids=[alert.id], limit=1)

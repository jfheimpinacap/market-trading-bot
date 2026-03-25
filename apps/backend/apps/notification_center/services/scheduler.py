from datetime import timedelta

from django.utils import timezone

from apps.notification_center.models import NotificationTriggerSource
from apps.notification_center.services.automation import get_or_create_automation_state
from apps.notification_center.services.delivery import send_digest_notifications
from apps.operator_alerts.services import build_digest


def run_digest_cycle(*, force: bool = False) -> dict:
    state = get_or_create_automation_state()
    if not state.is_enabled or not state.automatic_digest_enabled:
        return {'enabled': False, 'digest_created': False, 'deliveries': 0}

    now = timezone.now()
    last_cycle = state.last_digest_cycle_at
    interval = timedelta(minutes=state.digest_interval_minutes)

    if not force and last_cycle and now - last_cycle < interval:
        return {'enabled': True, 'digest_created': False, 'deliveries': 0, 'reason': 'interval_not_elapsed'}

    window_start = last_cycle or (now - interval)
    digest = build_digest(digest_type='cycle_window', window_start=window_start, window_end=now)
    deliveries = send_digest_notifications(digest, trigger_source=NotificationTriggerSource.DIGEST_AUTOMATION)

    state.last_digest_cycle_at = now
    state.save(update_fields=['last_digest_cycle_at', 'updated_at'])

    return {'enabled': True, 'digest_created': True, 'digest_id': digest.id, 'deliveries': len(deliveries)}

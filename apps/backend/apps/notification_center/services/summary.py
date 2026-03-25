from django.db.models import Count

from apps.notification_center.models import NotificationChannel, NotificationDelivery, NotificationDeliveryStatus, NotificationRule


def get_notification_summary() -> dict:
    deliveries = NotificationDelivery.objects.all()
    pending = deliveries.filter(delivery_status=NotificationDeliveryStatus.PENDING).count()
    failed = deliveries.filter(delivery_status=NotificationDeliveryStatus.FAILED).count()
    sent = deliveries.filter(delivery_status=NotificationDeliveryStatus.SENT).count()
    suppressed = deliveries.filter(delivery_status=NotificationDeliveryStatus.SUPPRESSED).count()

    by_channel = list(
        deliveries.values('channel__slug', 'channel__channel_type').annotate(count=Count('id')).order_by('-count', 'channel__slug')
    )

    return {
        'channels_enabled': NotificationChannel.objects.filter(is_enabled=True).count(),
        'rules_enabled': NotificationRule.objects.filter(is_enabled=True).count(),
        'deliveries_total': deliveries.count(),
        'deliveries_sent': sent,
        'deliveries_failed': failed,
        'deliveries_pending': pending,
        'deliveries_suppressed': suppressed,
        'by_channel': by_channel,
        'delivery_health': 'attention' if failed > 0 else 'healthy',
    }

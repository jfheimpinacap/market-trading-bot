from apps.notification_center.models import NotificationChannel, NotificationChannelType


def ensure_default_ui_channel() -> NotificationChannel:
    channel, _ = NotificationChannel.objects.get_or_create(
        slug='ui-only',
        defaults={
            'name': 'UI only',
            'channel_type': NotificationChannelType.UI_ONLY,
            'is_enabled': True,
            'config': {},
        },
    )
    return channel

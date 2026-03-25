from django.contrib import admin

from apps.notification_center.models import NotificationChannel, NotificationDelivery, NotificationRule


@admin.register(NotificationChannel)
class NotificationChannelAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug', 'channel_type', 'is_enabled', 'updated_at')
    search_fields = ('name', 'slug')
    list_filter = ('channel_type', 'is_enabled')


@admin.register(NotificationRule)
class NotificationRuleAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'is_enabled', 'delivery_mode', 'severity_threshold', 'cooldown_seconds', 'dedupe_window_seconds')
    search_fields = ('name',)
    list_filter = ('is_enabled', 'delivery_mode', 'severity_threshold')
    filter_horizontal = ('channels',)


@admin.register(NotificationDelivery)
class NotificationDeliveryAdmin(admin.ModelAdmin):
    list_display = ('id', 'channel', 'delivery_status', 'delivery_mode', 'related_alert', 'related_digest', 'created_at', 'delivered_at')
    search_fields = ('reason', 'fingerprint')
    list_filter = ('delivery_status', 'delivery_mode', 'channel__channel_type')

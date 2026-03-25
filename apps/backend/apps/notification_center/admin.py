from django.contrib import admin

from apps.notification_center.models import (
    NotificationAutomationState,
    NotificationChannel,
    NotificationDelivery,
    NotificationEscalationEvent,
    NotificationRule,
)


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
    list_display = ('id', 'channel', 'delivery_status', 'delivery_mode', 'trigger_source', 'related_alert', 'related_digest', 'created_at', 'delivered_at')
    search_fields = ('reason', 'fingerprint')
    list_filter = ('delivery_status', 'delivery_mode', 'trigger_source', 'channel__channel_type')


@admin.register(NotificationAutomationState)
class NotificationAutomationStateAdmin(admin.ModelAdmin):
    list_display = ('id', 'is_enabled', 'automatic_dispatch_enabled', 'automatic_digest_enabled', 'escalation_enabled', 'updated_at')


@admin.register(NotificationEscalationEvent)
class NotificationEscalationEventAdmin(admin.ModelAdmin):
    list_display = ('id', 'alert', 'severity', 'reason', 'status', 'created_at')
    search_fields = ('reason', 'alert__title', 'alert__source')
    list_filter = ('severity', 'status')

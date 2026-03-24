from django.contrib import admin

from apps.safety_guard.models import SafetyEvent, SafetyPolicyConfig


@admin.register(SafetyPolicyConfig)
class SafetyPolicyConfigAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'status', 'kill_switch_enabled', 'hard_stop_active', 'cooldown_until_cycle', 'updated_at')


@admin.register(SafetyEvent)
class SafetyEventAdmin(admin.ModelAdmin):
    list_display = ('id', 'event_type', 'severity', 'source', 'message', 'created_at')
    list_filter = ('event_type', 'severity', 'source')
    search_fields = ('message',)

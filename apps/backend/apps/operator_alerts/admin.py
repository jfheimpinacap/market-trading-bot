from django.contrib import admin

from apps.operator_alerts.models import OperatorAlert, OperatorDigest


@admin.register(OperatorAlert)
class OperatorAlertAdmin(admin.ModelAdmin):
    list_display = ('id', 'alert_type', 'severity', 'status', 'source', 'title', 'last_seen_at')
    search_fields = ('title', 'summary', 'dedupe_key')
    list_filter = ('status', 'severity', 'alert_type', 'source')


@admin.register(OperatorDigest)
class OperatorDigestAdmin(admin.ModelAdmin):
    list_display = ('id', 'digest_type', 'window_start', 'window_end', 'alerts_count', 'critical_count')
    list_filter = ('digest_type',)

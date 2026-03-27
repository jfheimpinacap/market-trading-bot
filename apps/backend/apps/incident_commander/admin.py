from django.contrib import admin

from apps.incident_commander.models import DegradedModeState, IncidentAction, IncidentRecord, IncidentRecoveryRun


@admin.register(IncidentRecord)
class IncidentRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'incident_type', 'severity', 'status', 'source_app', 'last_seen_at')
    list_filter = ('status', 'severity', 'incident_type', 'source_app')
    search_fields = ('title', 'summary', 'dedupe_key', 'related_object_id')


@admin.register(IncidentAction)
class IncidentActionAdmin(admin.ModelAdmin):
    list_display = ('id', 'incident', 'action_type', 'action_status', 'created_at')
    list_filter = ('action_status', 'action_type')


@admin.register(IncidentRecoveryRun)
class IncidentRecoveryRunAdmin(admin.ModelAdmin):
    list_display = ('id', 'incident', 'run_status', 'trigger', 'created_at')
    list_filter = ('run_status', 'trigger')


@admin.register(DegradedModeState)
class DegradedModeStateAdmin(admin.ModelAdmin):
    list_display = ('id', 'state', 'mission_control_paused', 'auto_execution_enabled', 'rollout_enabled', 'updated_at')

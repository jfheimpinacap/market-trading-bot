from django.contrib import admin

from apps.mission_control.models import MissionControlCycle, MissionControlSession, MissionControlState, MissionControlStep


@admin.register(MissionControlState)
class MissionControlStateAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'active_session', 'cycle_in_progress', 'updated_at')


@admin.register(MissionControlSession)
class MissionControlSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'started_at', 'finished_at', 'cycle_count', 'last_cycle_at')


@admin.register(MissionControlCycle)
class MissionControlCycleAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'cycle_number', 'status', 'opportunities_built', 'queue_count', 'auto_execute_count', 'blocked_count')


@admin.register(MissionControlStep)
class MissionControlStepAdmin(admin.ModelAdmin):
    list_display = ('id', 'cycle', 'step_type', 'status', 'started_at', 'finished_at')

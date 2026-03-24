from django.contrib import admin

from apps.continuous_demo.models import ContinuousDemoCycleRun, ContinuousDemoSession, LoopRuntimeControl


@admin.register(ContinuousDemoSession)
class ContinuousDemoSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'session_status', 'started_at', 'finished_at', 'total_cycles', 'total_auto_executed', 'total_errors')
    list_filter = ('session_status',)


@admin.register(ContinuousDemoCycleRun)
class ContinuousDemoCycleRunAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'cycle_number', 'status', 'started_at', 'finished_at', 'auto_executed_count')
    list_filter = ('status',)


@admin.register(LoopRuntimeControl)
class LoopRuntimeControlAdmin(admin.ModelAdmin):
    list_display = ('id', 'runtime_status', 'enabled', 'kill_switch', 'active_session', 'cycle_in_progress', 'last_heartbeat_at')

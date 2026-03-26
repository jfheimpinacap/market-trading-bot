from django.contrib import admin

from apps.position_manager.models import PositionExitPlan, PositionLifecycleDecision, PositionLifecycleRun


@admin.register(PositionLifecycleRun)
class PositionLifecycleRunAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'watched_positions', 'decisions_count', 'created_at')


@admin.register(PositionLifecycleDecision)
class PositionLifecycleDecisionAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'paper_position', 'decision_confidence', 'created_at')


@admin.register(PositionExitPlan)
class PositionExitPlanAdmin(admin.ModelAdmin):
    list_display = ('id', 'action', 'queue_required', 'auto_execute_allowed', 'created_at')

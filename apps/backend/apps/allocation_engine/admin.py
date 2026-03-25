from django.contrib import admin

from apps.allocation_engine.models import AllocationDecision, AllocationRun


@admin.register(AllocationRun)
class AllocationRunAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'scope_type', 'triggered_from', 'proposals_considered', 'proposals_selected', 'allocated_total', 'started_at')
    list_filter = ('status', 'scope_type', 'triggered_from')


@admin.register(AllocationDecision)
class AllocationDecisionAdmin(admin.ModelAdmin):
    list_display = ('id', 'run', 'proposal', 'rank', 'decision', 'final_allocated_quantity', 'created_at')
    list_filter = ('decision',)

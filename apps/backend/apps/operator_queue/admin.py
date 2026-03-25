from django.contrib import admin

from apps.operator_queue.models import OperatorDecisionLog, OperatorQueueItem


@admin.register(OperatorQueueItem)
class OperatorQueueItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'priority', 'source', 'queue_type', 'headline', 'created_at')
    list_filter = ('status', 'priority', 'source', 'queue_type')
    search_fields = ('headline', 'summary')


@admin.register(OperatorDecisionLog)
class OperatorDecisionLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'queue_item', 'decision', 'decided_by', 'created_at')
    list_filter = ('decision', 'decided_by')

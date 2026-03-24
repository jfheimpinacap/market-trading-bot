from django.contrib import admin

from apps.learning_memory.models import LearningAdjustment, LearningMemoryEntry


@admin.register(LearningMemoryEntry)
class LearningMemoryEntryAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'memory_type',
        'source_type',
        'provider',
        'market',
        'outcome',
        'score_delta',
        'confidence_delta',
        'quantity_bias_delta',
        'created_at',
    )
    list_filter = ('memory_type', 'outcome', 'source_type', 'provider')
    search_fields = ('summary', 'rationale', 'market__title', 'provider__name')


@admin.register(LearningAdjustment)
class LearningAdjustmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'adjustment_type', 'scope_type', 'scope_key', 'is_active', 'magnitude', 'reason', 'updated_at')
    list_filter = ('adjustment_type', 'scope_type', 'is_active')
    search_fields = ('scope_key', 'reason')

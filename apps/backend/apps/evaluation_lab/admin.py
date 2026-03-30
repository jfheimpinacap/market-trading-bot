from django.contrib import admin

from apps.evaluation_lab.models import (
    CalibrationBucket,
    EffectivenessMetric,
    EvaluationMetricSet,
    EvaluationRecommendation,
    EvaluationRun,
    EvaluationRuntimeRun,
    OutcomeAlignmentRecord,
)


@admin.register(EvaluationRun)
class EvaluationRunAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'status',
        'evaluation_scope',
        'market_scope',
        'started_at',
        'finished_at',
        'related_continuous_session',
        'related_semi_auto_run',
    )
    list_filter = ('status', 'evaluation_scope', 'market_scope')
    search_fields = ('summary',)
    ordering = ('-started_at', '-id')


@admin.register(EvaluationMetricSet)
class EvaluationMetricSetAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'run',
        'proposals_generated',
        'auto_executed_count',
        'blocked_count',
        'favorable_reviews_count',
        'unfavorable_reviews_count',
        'total_pnl',
        'equity_delta',
        'safety_events_count',
    )
    list_filter = ('run__evaluation_scope', 'run__market_scope', 'run__status')
    ordering = ('-run__started_at', '-id')


@admin.register(EvaluationRuntimeRun)
class EvaluationRuntimeRunAdmin(admin.ModelAdmin):
    list_display = ('id', 'started_at', 'completed_at', 'resolved_market_count', 'metric_count', 'drift_flag_count')
    ordering = ('-started_at', '-id')


@admin.register(OutcomeAlignmentRecord)
class OutcomeAlignmentRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'run', 'linked_market', 'resolved_outcome', 'alignment_status', 'created_at')
    list_filter = ('alignment_status', 'resolved_outcome')
    ordering = ('-created_at', '-id')


@admin.register(CalibrationBucket)
class CalibrationBucketAdmin(admin.ModelAdmin):
    list_display = ('id', 'run', 'bucket_label', 'segment_scope', 'segment_value', 'sample_count', 'calibration_gap')
    list_filter = ('segment_scope',)
    ordering = ('-created_at', '-id')


@admin.register(EffectivenessMetric)
class EffectivenessMetricAdmin(admin.ModelAdmin):
    list_display = ('id', 'run', 'metric_type', 'metric_scope', 'metric_value', 'sample_count', 'status')
    list_filter = ('metric_type', 'metric_scope', 'status')
    ordering = ('-created_at', '-id')


@admin.register(EvaluationRecommendation)
class EvaluationRecommendationAdmin(admin.ModelAdmin):
    list_display = ('id', 'run', 'recommendation_type', 'confidence', 'created_at')
    list_filter = ('recommendation_type',)
    ordering = ('-created_at', '-id')

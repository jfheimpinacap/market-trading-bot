from django.contrib import admin

from apps.evaluation_lab.models import EvaluationMetricSet, EvaluationRun


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

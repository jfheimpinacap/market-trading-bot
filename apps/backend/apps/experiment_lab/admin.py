from django.contrib import admin

from apps.experiment_lab.models import ExperimentRun, StrategyProfile


@admin.register(StrategyProfile)
class StrategyProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug', 'profile_type', 'market_scope', 'is_active', 'updated_at')
    list_filter = ('profile_type', 'market_scope', 'is_active')
    search_fields = ('name', 'slug', 'description')


@admin.register(ExperimentRun)
class ExperimentRunAdmin(admin.ModelAdmin):
    list_display = ('id', 'strategy_profile', 'run_type', 'status', 'started_at', 'finished_at', 'created_at')
    list_filter = ('run_type', 'status')
    search_fields = ('summary',)

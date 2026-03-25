from django.contrib import admin

from apps.real_market_ops.models import RealMarketOperationRun, RealScopeConfig


@admin.register(RealScopeConfig)
class RealScopeConfigAdmin(admin.ModelAdmin):
    list_display = ('id', 'enabled', 'provider_scope', 'market_scope', 'updated_at')


@admin.register(RealMarketOperationRun)
class RealMarketOperationRunAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'triggered_from', 'started_at', 'markets_considered', 'markets_eligible', 'auto_executed_count')
    list_filter = ('status', 'triggered_from')

from django.contrib import admin

from apps.portfolio_governor.models import PortfolioExposureSnapshot, PortfolioGovernanceRun, PortfolioThrottleDecision


@admin.register(PortfolioExposureSnapshot)
class PortfolioExposureSnapshotAdmin(admin.ModelAdmin):
    list_display = ('id', 'open_positions', 'total_exposure', 'concentration_market_ratio', 'recent_drawdown_pct', 'created_at_snapshot')


@admin.register(PortfolioThrottleDecision)
class PortfolioThrottleDecisionAdmin(admin.ModelAdmin):
    list_display = ('id', 'state', 'recommended_max_new_positions', 'recommended_max_size_multiplier', 'created_at_decision')


@admin.register(PortfolioGovernanceRun)
class PortfolioGovernanceRunAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'profile_slug', 'started_at', 'finished_at')

from django.contrib import admin

from apps.portfolio_governor.models import (
    PortfolioExposureClusterSnapshot,
    PortfolioExposureConflictReview,
    PortfolioExposureCoordinationRun,
    PortfolioExposureDecision,
    PortfolioExposureRecommendation,
    PortfolioExposureSnapshot,
    PortfolioGovernanceRun,
    PortfolioThrottleDecision,
    SessionExposureContribution,
)


@admin.register(PortfolioExposureSnapshot)
class PortfolioExposureSnapshotAdmin(admin.ModelAdmin):
    list_display = ('id', 'open_positions', 'total_exposure', 'concentration_market_ratio', 'recent_drawdown_pct', 'created_at_snapshot')


@admin.register(PortfolioThrottleDecision)
class PortfolioThrottleDecisionAdmin(admin.ModelAdmin):
    list_display = ('id', 'state', 'recommended_max_new_positions', 'recommended_max_size_multiplier', 'created_at_decision')


@admin.register(PortfolioGovernanceRun)
class PortfolioGovernanceRunAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'profile_slug', 'started_at', 'finished_at')


@admin.register(PortfolioExposureCoordinationRun)
class PortfolioExposureCoordinationRunAdmin(admin.ModelAdmin):
    list_display = ('id', 'started_at', 'completed_at', 'considered_cluster_count', 'concentration_alert_count', 'conflict_alert_count')


@admin.register(PortfolioExposureClusterSnapshot)
class PortfolioExposureClusterSnapshotAdmin(admin.ModelAdmin):
    list_display = ('id', 'cluster_label', 'cluster_type', 'net_direction', 'session_count', 'pending_dispatch_count', 'concentration_status')


@admin.register(SessionExposureContribution)
class SessionExposureContributionAdmin(admin.ModelAdmin):
    list_display = ('id', 'linked_session', 'contribution_role', 'contribution_direction', 'contribution_strength', 'created_at_snapshot')


@admin.register(PortfolioExposureConflictReview)
class PortfolioExposureConflictReviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'linked_cluster_snapshot', 'review_type', 'review_severity', 'created_at_review')


@admin.register(PortfolioExposureDecision)
class PortfolioExposureDecisionAdmin(admin.ModelAdmin):
    list_display = ('id', 'linked_cluster_snapshot', 'decision_type', 'decision_status', 'auto_applicable', 'created_at_decision')


@admin.register(PortfolioExposureRecommendation)
class PortfolioExposureRecommendationAdmin(admin.ModelAdmin):
    list_display = ('id', 'recommendation_type', 'confidence', 'created_at')

from django.contrib import admin

from apps.trust_calibration.models import AutomationFeedbackSnapshot, TrustCalibrationRecommendation, TrustCalibrationRun


@admin.register(TrustCalibrationRun)
class TrustCalibrationRunAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'window_days', 'profile_slug', 'started_at', 'finished_at')
    search_fields = ('profile_slug', 'runbook_template_slug', 'summary')


@admin.register(AutomationFeedbackSnapshot)
class AutomationFeedbackSnapshotAdmin(admin.ModelAdmin):
    list_display = ('id', 'run', 'action_type', 'current_trust_tier', 'approvals_granted', 'approvals_rejected', 'auto_actions_executed')
    search_fields = ('action_type', 'source_type', 'runbook_template_slug')


@admin.register(TrustCalibrationRecommendation)
class TrustCalibrationRecommendationAdmin(admin.ModelAdmin):
    list_display = ('id', 'run', 'action_type', 'recommendation_type', 'current_trust_tier', 'recommended_trust_tier', 'confidence')
    search_fields = ('action_type', 'recommendation_type')

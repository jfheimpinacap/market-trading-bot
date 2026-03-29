from django.contrib import admin

from apps.autonomy_advisory_resolution.models import AdvisoryResolution, AdvisoryResolutionRecommendation, AdvisoryResolutionRun


@admin.register(AdvisoryResolution)
class AdvisoryResolutionAdmin(admin.ModelAdmin):
    list_display = ('id', 'advisory_artifact', 'resolution_status', 'resolution_type', 'insight', 'campaign', 'updated_at')
    list_filter = ('resolution_status', 'resolution_type')
    search_fields = ('advisory_artifact__summary', 'insight__summary', 'campaign__title', 'rationale')


@admin.register(AdvisoryResolutionRecommendation)
class AdvisoryResolutionRecommendationAdmin(admin.ModelAdmin):
    list_display = ('id', 'recommendation_type', 'advisory_artifact', 'insight', 'created_at')
    list_filter = ('recommendation_type',)
    search_fields = ('rationale',)


@admin.register(AdvisoryResolutionRun)
class AdvisoryResolutionRunAdmin(admin.ModelAdmin):
    list_display = ('id', 'candidate_count', 'pending_count', 'acknowledged_count', 'adopted_count', 'created_at')

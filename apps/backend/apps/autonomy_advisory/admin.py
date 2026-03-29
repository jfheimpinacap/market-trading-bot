from django.contrib import admin

from .models import AdvisoryArtifact, AdvisoryRecommendation, AdvisoryRun


@admin.register(AdvisoryArtifact)
class AdvisoryArtifactAdmin(admin.ModelAdmin):
    list_display = ('id', 'artifact_type', 'artifact_status', 'target_scope', 'insight', 'created_at')
    list_filter = ('artifact_type', 'artifact_status', 'target_scope')
    search_fields = ('summary', 'rationale')


@admin.register(AdvisoryRecommendation)
class AdvisoryRecommendationAdmin(admin.ModelAdmin):
    list_display = ('id', 'recommendation_type', 'artifact_type', 'campaign_insight', 'created_at')
    list_filter = ('recommendation_type', 'artifact_type')
    search_fields = ('rationale',)


@admin.register(AdvisoryRun)
class AdvisoryRunAdmin(admin.ModelAdmin):
    list_display = ('id', 'candidate_count', 'ready_count', 'emitted_count', 'created_at')

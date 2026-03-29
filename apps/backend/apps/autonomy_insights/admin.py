from django.contrib import admin

from apps.autonomy_insights.models import CampaignInsight, InsightRecommendation, InsightRun


@admin.register(CampaignInsight)
class CampaignInsightAdmin(admin.ModelAdmin):
    list_display = ('id', 'insight_type', 'scope', 'campaign', 'recommendation_target', 'reviewed', 'created_at')
    list_filter = ('insight_type', 'scope', 'recommendation_target', 'reviewed')
    search_fields = ('summary', 'recommended_followup', 'campaign__title')


@admin.register(InsightRun)
class InsightRunAdmin(admin.ModelAdmin):
    list_display = ('id', 'candidate_count', 'lifecycle_closed_count', 'insight_count', 'created_at')


@admin.register(InsightRecommendation)
class InsightRecommendationAdmin(admin.ModelAdmin):
    list_display = ('id', 'recommendation_type', 'insight_type', 'target_campaign', 'created_at')
    list_filter = ('recommendation_type', 'insight_type')

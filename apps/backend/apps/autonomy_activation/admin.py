from django.contrib import admin

from apps.autonomy_activation.models import ActivationRecommendation, ActivationRun, CampaignActivation


@admin.register(CampaignActivation)
class CampaignActivationAdmin(admin.ModelAdmin):
    list_display = ('id', 'campaign', 'activation_status', 'trigger_source', 'activated_at', 'created_at')
    list_filter = ('activation_status', 'trigger_source')
    search_fields = ('campaign__title', 'activated_by', 'dispatch_rationale', 'failure_message')


@admin.register(ActivationRun)
class ActivationRunAdmin(admin.ModelAdmin):
    list_display = ('id', 'candidate_count', 'ready_count', 'blocked_count', 'expired_count', 'created_at')


@admin.register(ActivationRecommendation)
class ActivationRecommendationAdmin(admin.ModelAdmin):
    list_display = ('id', 'recommendation_type', 'target_campaign', 'confidence', 'created_at')
    list_filter = ('recommendation_type',)

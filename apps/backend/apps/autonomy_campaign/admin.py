from django.contrib import admin

from apps.autonomy_campaign import models


@admin.register(models.AutonomyCampaign)
class AutonomyCampaignAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'source_type', 'status', 'current_wave', 'created_at')
    search_fields = ('title', 'source_object_id')
    list_filter = ('status', 'source_type')


@admin.register(models.AutonomyCampaignStep)
class AutonomyCampaignStepAdmin(admin.ModelAdmin):
    list_display = ('id', 'campaign', 'step_order', 'wave', 'domain_slug', 'action_type', 'status')
    list_filter = ('status', 'action_type')

    @staticmethod
    def domain_slug(obj):
        return obj.domain.slug if obj.domain_id else 'n/a'


@admin.register(models.AutonomyCampaignCheckpoint)
class AutonomyCampaignCheckpointAdmin(admin.ModelAdmin):
    list_display = ('id', 'campaign', 'step', 'checkpoint_type', 'status', 'created_at')
    list_filter = ('checkpoint_type', 'status')

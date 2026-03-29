from django.contrib import admin

from apps.autonomy_operations.models import CampaignAttentionSignal, CampaignRuntimeSnapshot, OperationsRecommendation, OperationsRun

admin.site.register(CampaignRuntimeSnapshot)
admin.site.register(CampaignAttentionSignal)
admin.site.register(OperationsRun)
admin.site.register(OperationsRecommendation)

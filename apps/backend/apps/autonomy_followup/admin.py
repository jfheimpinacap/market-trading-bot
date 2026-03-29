from django.contrib import admin

from apps.autonomy_followup.models import CampaignFollowup, FollowupRecommendation, FollowupRun

admin.site.register(CampaignFollowup)
admin.site.register(FollowupRun)
admin.site.register(FollowupRecommendation)

from django.contrib import admin

from apps.autonomy_disposition.models import CampaignDisposition, DispositionRecommendation, DispositionRun

admin.site.register(CampaignDisposition)
admin.site.register(DispositionRun)
admin.site.register(DispositionRecommendation)

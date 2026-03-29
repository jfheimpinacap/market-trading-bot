from django.contrib import admin

from apps.autonomy_closeout.models import CampaignCloseoutReport, CloseoutFinding, CloseoutRecommendation, CloseoutRun


admin.site.register(CampaignCloseoutReport)
admin.site.register(CloseoutFinding)
admin.site.register(CloseoutRecommendation)
admin.site.register(CloseoutRun)

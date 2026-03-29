from django.contrib import admin

from apps.autonomy_scheduler.models import AdmissionRecommendation, CampaignAdmission, ChangeWindow, SchedulerRun

admin.site.register(CampaignAdmission)
admin.site.register(ChangeWindow)
admin.site.register(SchedulerRun)
admin.site.register(AdmissionRecommendation)

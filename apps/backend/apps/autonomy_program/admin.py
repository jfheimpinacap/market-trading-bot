from django.contrib import admin

from apps.autonomy_program.models import AutonomyProgramState, CampaignConcurrencyRule, CampaignHealthSnapshot, ProgramRecommendation


admin.site.register(AutonomyProgramState)
admin.site.register(CampaignConcurrencyRule)
admin.site.register(CampaignHealthSnapshot)
admin.site.register(ProgramRecommendation)

from django.contrib import admin

from apps.autonomy_intervention.models import (
    CampaignInterventionAction,
    CampaignInterventionRequest,
    InterventionOutcome,
    InterventionRun,
)

admin.site.register(CampaignInterventionRequest)
admin.site.register(CampaignInterventionAction)
admin.site.register(InterventionRun)
admin.site.register(InterventionOutcome)

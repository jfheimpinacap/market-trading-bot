from django.contrib import admin

from apps.opportunity_supervisor.models import OpportunityCycleItem, OpportunityCycleRun, OpportunityExecutionPlan

admin.site.register(OpportunityCycleRun)
admin.site.register(OpportunityCycleItem)
admin.site.register(OpportunityExecutionPlan)

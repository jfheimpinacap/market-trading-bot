from django.contrib import admin

from apps.rollout_manager.models import RolloutDecision, RolloutGuardrailEvent, StackRolloutPlan, StackRolloutRun

admin.site.register(StackRolloutPlan)
admin.site.register(StackRolloutRun)
admin.site.register(RolloutGuardrailEvent)
admin.site.register(RolloutDecision)

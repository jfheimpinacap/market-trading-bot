from django.contrib import admin

from apps.policy_rollout.models import PolicyBaselineSnapshot, PolicyPostChangeSnapshot, PolicyRolloutRecommendation, PolicyRolloutRun

admin.site.register(PolicyRolloutRun)
admin.site.register(PolicyBaselineSnapshot)
admin.site.register(PolicyPostChangeSnapshot)
admin.site.register(PolicyRolloutRecommendation)

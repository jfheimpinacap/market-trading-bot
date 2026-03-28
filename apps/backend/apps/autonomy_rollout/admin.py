from django.contrib import admin

from apps.autonomy_rollout.models import (
    AutonomyBaselineSnapshot,
    AutonomyPostChangeSnapshot,
    AutonomyRolloutRecommendation,
    AutonomyRolloutRun,
)

admin.site.register(AutonomyRolloutRun)
admin.site.register(AutonomyBaselineSnapshot)
admin.site.register(AutonomyPostChangeSnapshot)
admin.site.register(AutonomyRolloutRecommendation)

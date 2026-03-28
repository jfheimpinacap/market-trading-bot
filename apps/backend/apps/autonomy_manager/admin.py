from django.contrib import admin

from apps.autonomy_manager import models

admin.site.register(models.AutonomyDomain)
admin.site.register(models.AutonomyEnvelope)
admin.site.register(models.AutonomyStageState)
admin.site.register(models.AutonomyStageRecommendation)
admin.site.register(models.AutonomyStageTransition)

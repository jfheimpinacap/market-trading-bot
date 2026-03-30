from django.contrib import admin

from apps.prediction_agent.models import (
    PredictionFeatureSnapshot,
    PredictionModelProfile,
    PredictionRun,
    PredictionRuntimeAssessment,
    PredictionRuntimeCandidate,
    PredictionRuntimeRecommendation,
    PredictionRuntimeRun,
    PredictionScore,
)

admin.site.register(PredictionModelProfile)
admin.site.register(PredictionRun)
admin.site.register(PredictionFeatureSnapshot)
admin.site.register(PredictionScore)
admin.site.register(PredictionRuntimeRun)
admin.site.register(PredictionRuntimeCandidate)
admin.site.register(PredictionRuntimeAssessment)
admin.site.register(PredictionRuntimeRecommendation)

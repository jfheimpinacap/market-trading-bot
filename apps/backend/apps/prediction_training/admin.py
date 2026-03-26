from django.contrib import admin

from apps.prediction_training.models import (
    ModelComparisonResult,
    ModelComparisonRun,
    ModelEvaluationProfile,
    PredictionDatasetRun,
    PredictionModelArtifact,
    PredictionTrainingRun,
)

admin.site.register(PredictionDatasetRun)
admin.site.register(PredictionTrainingRun)
admin.site.register(PredictionModelArtifact)
admin.site.register(ModelEvaluationProfile)
admin.site.register(ModelComparisonRun)
admin.site.register(ModelComparisonResult)

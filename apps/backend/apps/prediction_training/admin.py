from django.contrib import admin

from apps.prediction_training.models import PredictionDatasetRun, PredictionModelArtifact, PredictionTrainingRun

admin.site.register(PredictionDatasetRun)
admin.site.register(PredictionTrainingRun)
admin.site.register(PredictionModelArtifact)

from django.db import models

from apps.common.models import TimeStampedModel


class PredictionTrainingStatus(models.TextChoices):
    RUNNING = 'running', 'Running'
    SUCCESS = 'success', 'Success'
    FAILED = 'failed', 'Failed'


class PredictionModelType(models.TextChoices):
    HEURISTIC = 'heuristic', 'Heuristic'
    XGBOOST = 'xgboost', 'XGBoost'
    FUTURE = 'future', 'Future'


class PredictionDatasetRun(TimeStampedModel):
    name = models.CharField(max_length=120)
    status = models.CharField(max_length=16, choices=PredictionTrainingStatus.choices, default=PredictionTrainingStatus.SUCCESS)
    label_definition = models.CharField(max_length=120)
    feature_set_version = models.CharField(max_length=64, default='prediction_features_v1')
    snapshot_horizon_hours = models.PositiveIntegerField(default=24)
    rows_built = models.PositiveIntegerField(default=0)
    positive_rows = models.PositiveIntegerField(default=0)
    negative_rows = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)
    period_start = models.DateTimeField(null=True, blank=True)
    period_end = models.DateTimeField(null=True, blank=True)
    feature_names = models.JSONField(default=list, blank=True)
    artifact_path = models.CharField(max_length=255, blank=True)
    summary = models.TextField(blank=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']


class PredictionTrainingRun(TimeStampedModel):
    status = models.CharField(max_length=16, choices=PredictionTrainingStatus.choices, default=PredictionTrainingStatus.RUNNING)
    dataset_run = models.ForeignKey(PredictionDatasetRun, on_delete=models.PROTECT, related_name='training_runs')
    model_type = models.CharField(max_length=24, choices=PredictionModelType.choices, default=PredictionModelType.XGBOOST)
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)
    rows_used = models.PositiveIntegerField(default=0)
    artifact_created = models.BooleanField(default=False)
    validation_summary = models.JSONField(default=dict, blank=True)
    summary = models.TextField(blank=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']


class PredictionModelArtifact(TimeStampedModel):
    name = models.CharField(max_length=120)
    version = models.CharField(max_length=64)
    model_type = models.CharField(max_length=24, choices=PredictionModelType.choices, default=PredictionModelType.XGBOOST)
    label_definition = models.CharField(max_length=120)
    feature_set_version = models.CharField(max_length=64)
    training_run = models.ForeignKey(PredictionTrainingRun, on_delete=models.PROTECT, related_name='artifacts')
    validation_metrics = models.JSONField(default=dict, blank=True)
    artifact_path = models.CharField(max_length=255)
    calibrator_path = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        constraints = [
            models.UniqueConstraint(fields=['name', 'version'], name='prediction_training_name_version_uniq'),
        ]

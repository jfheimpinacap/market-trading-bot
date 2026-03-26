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


class ModelComparisonStatus(models.TextChoices):
    RUNNING = 'running', 'Running'
    SUCCESS = 'success', 'Success'
    FAILED = 'failed', 'Failed'


class ModelComparisonScope(models.TextChoices):
    DEMO_ONLY = 'demo_only', 'Demo only'
    REAL_ONLY = 'real_only', 'Real only'
    MIXED = 'mixed', 'Mixed'


class ActiveModelRecommendationCode(models.TextChoices):
    KEEP_HEURISTIC = 'KEEP_HEURISTIC', 'Keep heuristic'
    KEEP_ACTIVE_MODEL = 'KEEP_ACTIVE_MODEL', 'Keep active model'
    ACTIVATE_CANDIDATE = 'ACTIVATE_CANDIDATE', 'Activate candidate'
    CAUTION_REVIEW_MANUALLY = 'CAUTION_REVIEW_MANUALLY', 'Caution review manually'


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


class ModelEvaluationProfile(TimeStampedModel):
    slug = models.SlugField(max_length=80, unique=True)
    name = models.CharField(max_length=120)
    description = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    config = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['slug']


class ModelComparisonRun(TimeStampedModel):
    status = models.CharField(max_length=16, choices=ModelComparisonStatus.choices, default=ModelComparisonStatus.RUNNING)
    scope = models.CharField(max_length=16, choices=ModelComparisonScope.choices, default=ModelComparisonScope.MIXED)
    evaluation_profile = models.ForeignKey(ModelEvaluationProfile, on_delete=models.PROTECT, related_name='comparison_runs')
    dataset_run = models.ForeignKey(
        PredictionDatasetRun,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='comparison_runs',
    )
    replay_run_id = models.PositiveIntegerField(null=True, blank=True)
    baseline_key = models.CharField(max_length=120)
    candidate_key = models.CharField(max_length=120)
    winner = models.CharField(max_length=24, blank=True, default='INCONCLUSIVE')
    recommendation_code = models.CharField(
        max_length=40,
        choices=ActiveModelRecommendationCode.choices,
        default=ActiveModelRecommendationCode.CAUTION_REVIEW_MANUALLY,
    )
    recommendation_reasons = models.JSONField(default=list, blank=True)
    metrics_summary = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)
    summary = models.TextField(blank=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class ModelComparisonResult(TimeStampedModel):
    run = models.ForeignKey(ModelComparisonRun, on_delete=models.CASCADE, related_name='results')
    predictor_key = models.CharField(max_length=120)
    predictor_label = models.CharField(max_length=120)
    predictor_type = models.CharField(max_length=24)
    profile_slug = models.CharField(max_length=80, blank=True)
    artifact = models.ForeignKey(
        PredictionModelArtifact,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='comparison_results',
    )
    metrics = models.JSONField(default=dict, blank=True)
    failures = models.PositiveIntegerField(default=0)
    coverage = models.DecimalField(max_digits=7, decimal_places=4, default=0)

    class Meta:
        ordering = ['run_id', 'id']

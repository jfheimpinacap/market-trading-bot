from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.common.models import TimeStampedModel


class PredictionRunStatus(models.TextChoices):
    SUCCESS = 'success', 'Success'
    PARTIAL = 'partial', 'Partial'
    FAILED = 'failed', 'Failed'


class PredictionConfidenceLevel(models.TextChoices):
    LOW = 'low', 'Low'
    MEDIUM = 'medium', 'Medium'
    HIGH = 'high', 'High'


class PredictionModelProfile(TimeStampedModel):
    slug = models.SlugField(max_length=80, unique=True)
    name = models.CharField(max_length=120)
    description = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    use_narrative = models.BooleanField(default=True)
    use_learning = models.BooleanField(default=True)
    calibration_alpha = models.DecimalField(max_digits=6, decimal_places=4, default=Decimal('1.0000'))
    calibration_beta = models.DecimalField(max_digits=6, decimal_places=4, default=Decimal('0.0000'))
    confidence_floor = models.DecimalField(max_digits=6, decimal_places=4, default=Decimal('0.2500'))
    confidence_cap = models.DecimalField(max_digits=6, decimal_places=4, default=Decimal('0.9500'))
    edge_strong_threshold = models.DecimalField(max_digits=6, decimal_places=4, default=Decimal('0.0800'))
    edge_neutral_threshold = models.DecimalField(max_digits=6, decimal_places=4, default=Decimal('0.0300'))
    weights = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['slug']


class PredictionRun(TimeStampedModel):
    status = models.CharField(max_length=16, choices=PredictionRunStatus.choices, default=PredictionRunStatus.SUCCESS)
    triggered_by = models.CharField(max_length=32, default='manual')
    model_profile = models.ForeignKey(PredictionModelProfile, on_delete=models.PROTECT, related_name='runs')
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)
    markets_scored = models.PositiveIntegerField(default=0)
    errors = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']


class PredictionFeatureSnapshot(TimeStampedModel):
    run = models.ForeignKey(PredictionRun, on_delete=models.CASCADE, related_name='feature_snapshots')
    market = models.ForeignKey('markets.Market', on_delete=models.CASCADE, related_name='prediction_feature_snapshots')
    snapshot = models.JSONField(default=dict, blank=True)
    source_type = models.CharField(max_length=24, blank=True)
    provider_slug = models.CharField(max_length=64, blank=True)
    stale_market_data = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['market', '-created_at'])]


class PredictionScore(TimeStampedModel):
    run = models.ForeignKey(PredictionRun, on_delete=models.CASCADE, related_name='scores')
    market = models.ForeignKey('markets.Market', on_delete=models.CASCADE, related_name='prediction_scores')
    model_profile = models.ForeignKey(PredictionModelProfile, on_delete=models.PROTECT, related_name='scores')
    feature_snapshot = models.ForeignKey(
        PredictionFeatureSnapshot,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='scores',
    )
    market_probability = models.DecimalField(
        max_digits=7,
        decimal_places=4,
        validators=[MinValueValidator(Decimal('0.0000')), MaxValueValidator(Decimal('1.0000'))],
    )
    system_probability = models.DecimalField(
        max_digits=7,
        decimal_places=4,
        validators=[MinValueValidator(Decimal('0.0000')), MaxValueValidator(Decimal('1.0000'))],
    )
    edge = models.DecimalField(max_digits=8, decimal_places=4)
    confidence = models.DecimalField(
        max_digits=7,
        decimal_places=4,
        validators=[MinValueValidator(Decimal('0.0000')), MaxValueValidator(Decimal('1.0000'))],
    )
    confidence_level = models.CharField(max_length=16, choices=PredictionConfidenceLevel.choices)
    edge_label = models.CharField(max_length=16, default='neutral')
    rationale = models.TextField(blank=True)
    narrative_contribution = models.DecimalField(max_digits=8, decimal_places=4, default=Decimal('0.0000'))
    model_profile_used = models.CharField(max_length=80)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['market', '-created_at']),
            models.Index(fields=['model_profile', '-created_at']),
            models.Index(fields=['edge', '-created_at']),
        ]


class PredictionOutcomeLabel(TimeStampedModel):
    score = models.ForeignKey(PredictionScore, on_delete=models.CASCADE, related_name='outcome_labels')
    label_type = models.CharField(max_length=40)
    label_value = models.CharField(max_length=120)
    resolved_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']

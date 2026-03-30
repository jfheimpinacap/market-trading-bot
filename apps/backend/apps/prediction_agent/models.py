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


class PredictionRuntimeModelMode(models.TextChoices):
    HEURISTIC_ONLY = 'heuristic_only', 'Heuristic only'
    MODEL_ONLY = 'model_only', 'Model only'
    BLENDED = 'blended', 'Blended'
    MODEL_WITH_HEURISTIC_FALLBACK = 'model_with_heuristic_fallback', 'Model with heuristic fallback'


class PredictionAssessmentStatus(models.TextChoices):
    STRONG_EDGE = 'STRONG_EDGE', 'Strong edge'
    WEAK_EDGE = 'WEAK_EDGE', 'Weak edge'
    LOW_CONFIDENCE = 'LOW_CONFIDENCE', 'Low confidence'
    NO_EDGE = 'NO_EDGE', 'No edge'
    CONFLICTED = 'CONFLICTED', 'Conflicted'
    NEEDS_REVIEW = 'NEEDS_REVIEW', 'Needs review'


class PredictionRuntimeRecommendationType(models.TextChoices):
    SEND_TO_RISK_ASSESSMENT = 'SEND_TO_RISK_ASSESSMENT', 'Send to risk assessment'
    SEND_TO_SIGNAL_FUSION = 'SEND_TO_SIGNAL_FUSION', 'Send to signal fusion'
    KEEP_FOR_MONITORING = 'KEEP_FOR_MONITORING', 'Keep for monitoring'
    IGNORE_NO_EDGE = 'IGNORE_NO_EDGE', 'Ignore no edge'
    IGNORE_LOW_CONFIDENCE = 'IGNORE_LOW_CONFIDENCE', 'Ignore low confidence'
    REQUIRE_MANUAL_PREDICTION_REVIEW = 'REQUIRE_MANUAL_PREDICTION_REVIEW', 'Require manual prediction review'
    REORDER_PREDICTION_PRIORITY = 'REORDER_PREDICTION_PRIORITY', 'Reorder prediction priority'


class PredictionRuntimeRun(TimeStampedModel):
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    candidate_count = models.PositiveIntegerField(default=0)
    scored_count = models.PositiveIntegerField(default=0)
    blocked_count = models.PositiveIntegerField(default=0)
    high_edge_count = models.PositiveIntegerField(default=0)
    low_confidence_count = models.PositiveIntegerField(default=0)
    sent_to_risk_count = models.PositiveIntegerField(default=0)
    sent_to_signal_fusion_count = models.PositiveIntegerField(default=0)
    recommendation_summary = models.JSONField(default=dict, blank=True)
    active_model_context = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']


class PredictionRuntimeCandidate(TimeStampedModel):
    runtime_run = models.ForeignKey(PredictionRuntimeRun, on_delete=models.CASCADE, related_name='candidates')
    linked_market = models.ForeignKey('markets.Market', on_delete=models.CASCADE, related_name='prediction_runtime_candidates')
    linked_research_candidate = models.ForeignKey(
        'research_agent.MarketResearchCandidate',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='prediction_runtime_candidates',
    )
    linked_scan_signals = models.JSONField(default=list, blank=True)
    market_provider = models.CharField(max_length=64, blank=True)
    category = models.CharField(max_length=100, blank=True)
    market_probability = models.DecimalField(
        max_digits=7,
        decimal_places=4,
        validators=[MinValueValidator(Decimal('0.0000')), MaxValueValidator(Decimal('1.0000'))],
        null=True,
        blank=True,
    )
    narrative_support_score = models.DecimalField(max_digits=6, decimal_places=4, null=True, blank=True)
    divergence_score = models.DecimalField(max_digits=6, decimal_places=4, null=True, blank=True)
    research_status = models.CharField(max_length=24, blank=True)
    candidate_quality_score = models.DecimalField(max_digits=7, decimal_places=4, default=Decimal('0.0000'))
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-candidate_quality_score', '-created_at', '-id']
        indexes = [
            models.Index(fields=['runtime_run', '-candidate_quality_score']),
            models.Index(fields=['linked_market', '-created_at']),
        ]


class PredictionRuntimeAssessment(TimeStampedModel):
    linked_candidate = models.ForeignKey(PredictionRuntimeCandidate, on_delete=models.CASCADE, related_name='assessments')
    active_model_name = models.CharField(max_length=120, blank=True)
    model_mode = models.CharField(max_length=48, choices=PredictionRuntimeModelMode.choices)
    system_probability = models.DecimalField(max_digits=7, decimal_places=4)
    calibrated_probability = models.DecimalField(max_digits=7, decimal_places=4)
    market_probability = models.DecimalField(max_digits=7, decimal_places=4)
    raw_edge = models.DecimalField(max_digits=8, decimal_places=4)
    adjusted_edge = models.DecimalField(max_digits=8, decimal_places=4)
    confidence_score = models.DecimalField(max_digits=7, decimal_places=4)
    uncertainty_score = models.DecimalField(max_digits=7, decimal_places=4)
    evidence_quality_score = models.DecimalField(max_digits=7, decimal_places=4)
    precedent_caution_score = models.DecimalField(max_digits=7, decimal_places=4)
    narrative_influence_score = models.DecimalField(max_digits=7, decimal_places=4)
    prediction_status = models.CharField(max_length=24, choices=PredictionAssessmentStatus.choices)
    rationale = models.TextField(blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    feature_summary = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['prediction_status', '-created_at']),
            models.Index(fields=['model_mode', '-created_at']),
        ]


class PredictionRuntimeRecommendation(TimeStampedModel):
    runtime_run = models.ForeignKey(PredictionRuntimeRun, on_delete=models.CASCADE, related_name='recommendations')
    target_assessment = models.ForeignKey(
        PredictionRuntimeAssessment,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='recommendations',
    )
    recommendation_type = models.CharField(max_length=64, choices=PredictionRuntimeRecommendationType.choices)
    rationale = models.TextField(blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.DecimalField(max_digits=6, decimal_places=4, default=Decimal('0.0000'))
    blockers = models.JSONField(default=list, blank=True)
    class Meta:
        ordering = ['-created_at', '-id']

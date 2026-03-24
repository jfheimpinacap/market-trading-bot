from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.common.models import TimeStampedModel
from apps.markets.models import Market, Provider
from apps.paper_trading.models import PaperTrade
from apps.postmortem_demo.models import TradeReview
from apps.signals.models import MarketSignal


class LearningMemoryType(models.TextChoices):
    SIGNAL_PATTERN = 'signal_pattern', 'Signal pattern'
    MARKET_PATTERN = 'market_pattern', 'Market pattern'
    PROVIDER_PATTERN = 'provider_pattern', 'Provider pattern'
    TRADE_PATTERN = 'trade_pattern', 'Trade pattern'
    POLICY_PATTERN = 'policy_pattern', 'Policy pattern'


class LearningSourceType(models.TextChoices):
    DEMO = 'demo', 'Demo'
    REAL_READ_ONLY = 'real_read_only', 'Real read only'
    MIXED = 'mixed', 'Mixed'


class LearningOutcome(models.TextChoices):
    POSITIVE = 'positive', 'Positive'
    NEUTRAL = 'neutral', 'Neutral'
    NEGATIVE = 'negative', 'Negative'


class LearningAdjustmentType(models.TextChoices):
    CONFIDENCE_BIAS = 'confidence_bias', 'Confidence bias'
    QUANTITY_BIAS = 'quantity_bias', 'Quantity bias'
    RISK_CAUTION_BIAS = 'risk_caution_bias', 'Risk caution bias'
    POLICY_CAUTION_BIAS = 'policy_caution_bias', 'Policy caution bias'


class LearningScopeType(models.TextChoices):
    GLOBAL = 'global', 'Global'
    PROVIDER = 'provider', 'Provider'
    MARKET = 'market', 'Market'
    SOURCE_TYPE = 'source_type', 'Source type'
    SIGNAL_TYPE = 'signal_type', 'Signal type'


class LearningMemoryEntry(TimeStampedModel):
    memory_type = models.CharField(max_length=32, choices=LearningMemoryType.choices)
    source_type = models.CharField(max_length=24, choices=LearningSourceType.choices, default=LearningSourceType.MIXED)
    provider = models.ForeignKey(Provider, null=True, blank=True, on_delete=models.SET_NULL, related_name='learning_memory_entries')
    market = models.ForeignKey(Market, null=True, blank=True, on_delete=models.SET_NULL, related_name='learning_memory_entries')
    related_trade = models.ForeignKey(PaperTrade, null=True, blank=True, on_delete=models.SET_NULL, related_name='learning_memory_entries')
    related_review = models.ForeignKey(TradeReview, null=True, blank=True, on_delete=models.SET_NULL, related_name='learning_memory_entries')
    related_signal = models.ForeignKey(MarketSignal, null=True, blank=True, on_delete=models.SET_NULL, related_name='learning_memory_entries')
    outcome = models.CharField(max_length=16, choices=LearningOutcome.choices)
    score_delta = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal('0.00'))
    confidence_delta = models.DecimalField(max_digits=7, decimal_places=4, default=Decimal('0.0000'))
    quantity_bias_delta = models.DecimalField(max_digits=7, decimal_places=4, default=Decimal('0.0000'))
    summary = models.CharField(max_length=255)
    rationale = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['memory_type', '-created_at']),
            models.Index(fields=['outcome', '-created_at']),
            models.Index(fields=['source_type', '-created_at']),
        ]


class LearningAdjustment(TimeStampedModel):
    adjustment_type = models.CharField(max_length=40, choices=LearningAdjustmentType.choices)
    scope_type = models.CharField(max_length=24, choices=LearningScopeType.choices)
    scope_key = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)
    magnitude = models.DecimalField(
        max_digits=7,
        decimal_places=4,
        validators=[MinValueValidator(Decimal('-1.0000')), MaxValueValidator(Decimal('1.0000'))],
    )
    reason = models.CharField(max_length=255)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-updated_at', '-id']
        indexes = [
            models.Index(fields=['adjustment_type', 'scope_type', 'scope_key']),
            models.Index(fields=['is_active', '-updated_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['adjustment_type', 'scope_type', 'scope_key'],
                name='learning_memory_unique_adjustment_scope',
            )
        ]


class LearningRebuildRun(TimeStampedModel):
    class Status(models.TextChoices):
        SUCCESS = 'SUCCESS', 'Success'
        PARTIAL = 'PARTIAL', 'Partial'
        FAILED = 'FAILED', 'Failed'

    class TriggeredFrom(models.TextChoices):
        MANUAL = 'manual', 'Manual'
        AUTOMATION = 'automation', 'Automation'
        CONTINUOUS_DEMO = 'continuous_demo', 'Continuous demo'
        EVALUATION = 'evaluation', 'Evaluation'
        POSTMORTEM = 'postmortem', 'Postmortem'

    status = models.CharField(max_length=12, choices=Status.choices, default=Status.SUCCESS)
    triggered_from = models.CharField(max_length=24, choices=TriggeredFrom.choices, default=TriggeredFrom.MANUAL)
    related_session = models.ForeignKey(
        'continuous_demo.ContinuousDemoSession',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='learning_rebuild_runs',
    )
    related_cycle = models.ForeignKey(
        'continuous_demo.ContinuousDemoCycleRun',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='learning_rebuild_runs',
    )
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)
    memory_entries_processed = models.PositiveIntegerField(default=0)
    adjustments_created = models.PositiveIntegerField(default=0)
    adjustments_updated = models.PositiveIntegerField(default=0)
    adjustments_deactivated = models.PositiveIntegerField(default=0)
    summary = models.CharField(max_length=255, blank=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']

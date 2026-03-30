from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.common.models import TimeStampedModel
from apps.markets.models import Market, Provider
from apps.paper_trading.models import PaperTrade
from apps.postmortem_agents.models import PostmortemBoardRun
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


class FailurePatternType(models.TextChoices):
    NARRATIVE_MISS = 'narrative_miss', 'Narrative miss'
    PREDICTION_OVERCONFIDENCE = 'prediction_overconfidence', 'Prediction overconfidence'
    WEAK_EDGE = 'weak_edge', 'Weak edge'
    LOW_LIQUIDITY_TRAP = 'low_liquidity_trap', 'Low liquidity trap'
    TIMING_DECAY = 'timing_decay', 'Timing decay'
    RUNTIME_GUARD_MISS = 'runtime_guard_miss', 'Runtime guard miss'
    RISK_SIZING_MISS = 'risk_sizing_miss', 'Risk sizing miss'
    EXECUTION_SLIPPAGE_MISS = 'execution_slippage_miss', 'Execution slippage miss'
    PRECEDENT_IGNORED = 'precedent_ignored', 'Precedent ignored'
    MULTI_FACTOR_FAILURE = 'multi_factor_failure', 'Multi factor failure'


class LearningLoopScope(models.TextChoices):
    GLOBAL = 'global', 'Global'
    PROVIDER = 'provider', 'Provider'
    CATEGORY = 'category', 'Category'
    SOURCE_TYPE = 'source_type', 'Source type'
    SIGNAL_TYPE = 'signal_type', 'Signal type'
    MARKET = 'market', 'Market'


class FailurePatternStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Active'
    WATCH = 'WATCH', 'Watch'
    EXPIRED = 'EXPIRED', 'Expired'
    NEEDS_REVIEW = 'NEEDS_REVIEW', 'Needs review'


class LoopAdjustmentStatus(models.TextChoices):
    PROPOSED = 'PROPOSED', 'Proposed'
    ACTIVE = 'ACTIVE', 'Active'
    PAUSED = 'PAUSED', 'Paused'
    EXPIRED = 'EXPIRED', 'Expired'
    REJECTED = 'REJECTED', 'Rejected'


class LoopAdjustmentType(models.TextChoices):
    CONFIDENCE_PENALTY = 'confidence_penalty', 'Confidence penalty'
    EDGE_PENALTY = 'edge_penalty', 'Edge penalty'
    LIQUIDITY_PENALTY = 'liquidity_penalty', 'Liquidity penalty'
    SOURCE_CONFIDENCE_PENALTY = 'source_confidence_penalty', 'Source confidence penalty'
    CATEGORY_CAUTION = 'category_caution', 'Category caution'
    PROVIDER_CAUTION = 'provider_caution', 'Provider caution'
    SIGNAL_TYPE_CAUTION = 'signal_type_caution', 'Signal type caution'
    RISK_SIZE_CAP = 'risk_size_cap', 'Risk size cap'
    WATCH_ESCALATION = 'watch_escalation', 'Watch escalation'
    MANUAL_REVIEW_TRIGGER = 'manual_review_trigger', 'Manual review trigger'


class LearningRecommendationType(models.TextChoices):
    ACTIVATE_ADJUSTMENT = 'ACTIVATE_ADJUSTMENT', 'Activate adjustment'
    KEEP_ADJUSTMENT_ON_WATCH = 'KEEP_ADJUSTMENT_ON_WATCH', 'Keep adjustment on watch'
    EXPIRE_ADJUSTMENT = 'EXPIRE_ADJUSTMENT', 'Expire adjustment'
    REQUIRE_MANUAL_LEARNING_REVIEW = 'REQUIRE_MANUAL_LEARNING_REVIEW', 'Require manual learning review'
    ATTACH_CAUTION_TO_PREDICTION = 'ATTACH_CAUTION_TO_PREDICTION', 'Attach caution to prediction'
    ATTACH_CAUTION_TO_RISK = 'ATTACH_CAUTION_TO_RISK', 'Attach caution to risk'
    REORDER_LEARNING_PRIORITY = 'REORDER_LEARNING_PRIORITY', 'Reorder learning priority'


class LearningApplicationTarget(models.TextChoices):
    RESEARCH = 'research', 'Research'
    PREDICTION = 'prediction', 'Prediction'
    RISK = 'risk', 'Risk'
    PROPOSAL = 'proposal', 'Proposal'
    SIGNAL_FUSION = 'signal_fusion', 'Signal fusion'


class LearningApplicationType(models.TextChoices):
    CAUTION_ATTACHED = 'caution_attached', 'Caution attached'
    SCORE_PENALTY_APPLIED = 'score_penalty_applied', 'Score penalty applied'
    MANUAL_REVIEW_REQUIRED = 'manual_review_required', 'Manual review required'
    SIZE_CAP_APPLIED = 'size_cap_applied', 'Size cap applied'
    WATCH_ESCALATION_APPLIED = 'watch_escalation_applied', 'Watch escalation applied'


class PostmortemLearningRun(TimeStampedModel):
    linked_postmortem_run = models.ForeignKey(PostmortemBoardRun, null=True, blank=True, on_delete=models.SET_NULL, related_name='learning_runs')
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    reviewed_position_count = models.PositiveIntegerField(default=0)
    failure_pattern_count = models.PositiveIntegerField(default=0)
    adjustment_count = models.PositiveIntegerField(default=0)
    active_adjustment_count = models.PositiveIntegerField(default=0)
    expired_adjustment_count = models.PositiveIntegerField(default=0)
    recommendation_summary = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']


class FailurePattern(TimeStampedModel):
    canonical_label = models.CharField(max_length=120)
    pattern_type = models.CharField(max_length=48, choices=FailurePatternType.choices)
    scope = models.CharField(max_length=24, choices=LearningLoopScope.choices, default=LearningLoopScope.GLOBAL)
    scope_key = models.CharField(max_length=120, default='global')
    severity_score = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    recurrence_count = models.PositiveIntegerField(default=1)
    evidence_summary = models.JSONField(default=dict, blank=True)
    linked_postmortems = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=24, choices=FailurePatternStatus.choices, default=FailurePatternStatus.WATCH)
    rationale = models.TextField(blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-updated_at', '-id']
        constraints = [
            models.UniqueConstraint(fields=['canonical_label', 'pattern_type', 'scope', 'scope_key'], name='learning_unique_failure_pattern_scope')
        ]


class PostmortemLearningAdjustment(TimeStampedModel):
    linked_failure_pattern = models.ForeignKey(FailurePattern, null=True, blank=True, on_delete=models.SET_NULL, related_name='adjustments')
    linked_postmortem = models.ForeignKey(PostmortemBoardRun, null=True, blank=True, on_delete=models.SET_NULL, related_name='learning_adjustments')
    adjustment_type = models.CharField(max_length=48, choices=LoopAdjustmentType.choices)
    scope = models.CharField(max_length=24, choices=LearningLoopScope.choices, default=LearningLoopScope.GLOBAL)
    scope_key = models.CharField(max_length=120, default='global')
    adjustment_strength = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal('0.0000'))
    status = models.CharField(max_length=24, choices=LoopAdjustmentStatus.choices, default=LoopAdjustmentStatus.PROPOSED)
    expiration_hint = models.DateTimeField(null=True, blank=True)
    rationale = models.TextField(blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-updated_at', '-id']
        indexes = [models.Index(fields=['status', '-updated_at']), models.Index(fields=['adjustment_type', 'scope', 'scope_key'])]


class LearningApplicationRecord(TimeStampedModel):
    linked_adjustment = models.ForeignKey(PostmortemLearningAdjustment, on_delete=models.CASCADE, related_name='application_records')
    target_component = models.CharField(max_length=24, choices=LearningApplicationTarget.choices)
    target_entity_id = models.CharField(max_length=120, blank=True)
    application_type = models.CharField(max_length=32, choices=LearningApplicationType.choices)
    before_value = models.CharField(max_length=120, blank=True)
    after_value = models.CharField(max_length=120, blank=True)
    rationale = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class LearningRecommendation(TimeStampedModel):
    recommendation_type = models.CharField(max_length=48, choices=LearningRecommendationType.choices)
    target_pattern = models.ForeignKey(FailurePattern, null=True, blank=True, on_delete=models.SET_NULL, related_name='recommendations')
    target_adjustment = models.ForeignKey(PostmortemLearningAdjustment, null=True, blank=True, on_delete=models.SET_NULL, related_name='recommendations')
    rationale = models.TextField(blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal('0.5000'))
    blockers = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']

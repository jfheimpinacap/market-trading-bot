from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.common.models import TimeStampedModel
from apps.markets.models import Market
from apps.paper_trading.models import PaperPosition
from apps.prediction_agent.models import PredictionScore
from apps.proposal_engine.models import TradeProposal


class RiskAssessmentStatus(models.TextChoices):
    READY = 'READY', 'Ready'
    SUCCESS = 'SUCCESS', 'Success'
    FAILED = 'FAILED', 'Failed'


class RiskLevel(models.TextChoices):
    LOW = 'LOW', 'Low'
    MEDIUM = 'MEDIUM', 'Medium'
    HIGH = 'HIGH', 'High'
    BLOCKED = 'BLOCKED', 'Blocked'


class RiskSizingMode(models.TextChoices):
    FIXED = 'fixed', 'Fixed'
    HEURISTIC = 'heuristic', 'Heuristic'
    KELLY_LIKE = 'kelly_like', 'Kelly-like'
    CAPPED = 'capped', 'Capped'


class PositionWatchEventType(models.TextChoices):
    MONITOR = 'monitor', 'Monitor'
    CAUTION = 'caution', 'Caution'
    REVIEW_REQUIRED = 'review_required', 'Review required'
    EXIT_CONSIDERATION = 'exit_consideration', 'Exit consideration'
    BLOCKED_CONTEXT = 'blocked_context', 'Blocked context'


class PositionWatchSeverity(models.TextChoices):
    INFO = 'info', 'Info'
    WARNING = 'warning', 'Warning'
    HIGH = 'high', 'High'


class RiskRuntimeApprovalStatus(models.TextChoices):
    APPROVED = 'APPROVED', 'Approved'
    APPROVED_REDUCED = 'APPROVED_REDUCED', 'Approved reduced'
    BLOCKED = 'BLOCKED', 'Blocked'
    NEEDS_REVIEW = 'NEEDS_REVIEW', 'Needs review'


class RiskRuntimeSizingMode(models.TextChoices):
    FIXED_FRACTION = 'fixed_fraction', 'Fixed fraction'
    BOUNDED_KELLY = 'bounded_kelly', 'Bounded Kelly'
    CAPPED_FRACTIONAL_KELLY = 'capped_fractional_kelly', 'Capped fractional Kelly'
    WATCH_ONLY = 'watch_only', 'Watch only'
    NO_TRADE = 'no_trade', 'No trade'


class PositionWatchPlanStatus(models.TextChoices):
    REQUIRED = 'REQUIRED', 'Required'
    OPTIONAL = 'OPTIONAL', 'Optional'
    NOT_NEEDED = 'NOT_NEEDED', 'Not needed'


class RiskRuntimeRecommendationType(models.TextChoices):
    APPROVE_FOR_PAPER_EXECUTION = 'APPROVE_FOR_PAPER_EXECUTION', 'Approve for paper execution'
    APPROVE_REDUCED_SIZE = 'APPROVE_REDUCED_SIZE', 'Approve reduced size'
    BLOCK_HIGH_RISK = 'BLOCK_HIGH_RISK', 'Block high risk'
    BLOCK_LOW_CONFIDENCE = 'BLOCK_LOW_CONFIDENCE', 'Block low confidence'
    BLOCK_POOR_LIQUIDITY = 'BLOCK_POOR_LIQUIDITY', 'Block poor liquidity'
    REQUIRE_MANUAL_RISK_REVIEW = 'REQUIRE_MANUAL_RISK_REVIEW', 'Require manual risk review'
    SEND_TO_EXECUTION_SIMULATOR = 'SEND_TO_EXECUTION_SIMULATOR', 'Send to execution simulator'
    KEEP_ON_WATCH = 'KEEP_ON_WATCH', 'Keep on watch'
    REORDER_RISK_PRIORITY = 'REORDER_RISK_PRIORITY', 'Reorder risk priority'


class RiskAssessment(TimeStampedModel):
    market = models.ForeignKey(Market, on_delete=models.SET_NULL, null=True, blank=True, related_name='risk_agent_assessments')
    proposal = models.ForeignKey(TradeProposal, on_delete=models.SET_NULL, null=True, blank=True, related_name='risk_agent_assessments')
    prediction_score = models.ForeignKey(PredictionScore, on_delete=models.SET_NULL, null=True, blank=True, related_name='risk_agent_assessments')
    assessment_status = models.CharField(max_length=12, choices=RiskAssessmentStatus.choices, default=RiskAssessmentStatus.READY)
    risk_level = models.CharField(max_length=12, choices=RiskLevel.choices, default=RiskLevel.MEDIUM)
    risk_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))])
    key_risk_factors = models.JSONField(default=list, blank=True)
    narrative_risk_summary = models.TextField(blank=True)
    liquidity_risk = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    volatility_or_momentum_risk = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    confidence_risk = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    provider_risk = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    runtime_risk = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    safety_context = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class RiskSizingDecision(TimeStampedModel):
    risk_assessment = models.ForeignKey(RiskAssessment, on_delete=models.CASCADE, related_name='sizing_decisions')
    base_quantity = models.DecimalField(max_digits=14, decimal_places=4)
    adjusted_quantity = models.DecimalField(max_digits=14, decimal_places=4)
    sizing_mode = models.CharField(max_length=16, choices=RiskSizingMode.choices, default=RiskSizingMode.HEURISTIC)
    sizing_rationale = models.TextField(blank=True)
    max_exposure_allowed = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    reserve_cash_considered = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    confidence_adjustment = models.DecimalField(max_digits=8, decimal_places=4, default=Decimal('1.0000'))
    liquidity_adjustment = models.DecimalField(max_digits=8, decimal_places=4, default=Decimal('1.0000'))
    safety_adjustment = models.DecimalField(max_digits=8, decimal_places=4, default=Decimal('1.0000'))
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class PositionWatchRun(TimeStampedModel):
    status = models.CharField(max_length=12, choices=RiskAssessmentStatus.choices, default=RiskAssessmentStatus.READY)
    watched_positions = models.PositiveIntegerField(default=0)
    generated_events = models.PositiveIntegerField(default=0)
    summary = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class PositionWatchEvent(TimeStampedModel):
    watch_run = models.ForeignKey(PositionWatchRun, on_delete=models.CASCADE, related_name='events')
    paper_position = models.ForeignKey(PaperPosition, on_delete=models.SET_NULL, null=True, blank=True, related_name='risk_watch_events')
    event_type = models.CharField(max_length=24, choices=PositionWatchEventType.choices)
    severity = models.CharField(max_length=12, choices=PositionWatchSeverity.choices, default=PositionWatchSeverity.INFO)
    summary = models.CharField(max_length=255)
    rationale = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class RiskRuntimeRun(TimeStampedModel):
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    candidate_count = models.PositiveIntegerField(default=0)
    approved_count = models.PositiveIntegerField(default=0)
    blocked_count = models.PositiveIntegerField(default=0)
    reduced_size_count = models.PositiveIntegerField(default=0)
    watch_required_count = models.PositiveIntegerField(default=0)
    sent_to_execution_sim_count = models.PositiveIntegerField(default=0)
    recommendation_summary = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']


class RiskRuntimeCandidate(TimeStampedModel):
    runtime_run = models.ForeignKey(RiskRuntimeRun, on_delete=models.CASCADE, related_name='candidates')
    linked_prediction_assessment = models.ForeignKey(
        'prediction_agent.PredictionRuntimeAssessment',
        on_delete=models.CASCADE,
        related_name='risk_runtime_candidates',
    )
    linked_market = models.ForeignKey('markets.Market', on_delete=models.CASCADE, related_name='risk_runtime_candidates')
    market_provider = models.CharField(max_length=64, blank=True)
    category = models.CharField(max_length=100, blank=True)
    calibrated_probability = models.DecimalField(max_digits=7, decimal_places=4)
    adjusted_edge = models.DecimalField(max_digits=8, decimal_places=4)
    confidence_score = models.DecimalField(max_digits=7, decimal_places=4)
    uncertainty_score = models.DecimalField(max_digits=7, decimal_places=4)
    evidence_quality_score = models.DecimalField(max_digits=7, decimal_places=4)
    precedent_caution_score = models.DecimalField(max_digits=7, decimal_places=4)
    market_liquidity_context = models.JSONField(default=dict, blank=True)
    time_to_resolution = models.PositiveIntegerField(null=True, blank=True)
    predicted_status = models.CharField(max_length=24, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['runtime_run', '-created_at']),
            models.Index(fields=['linked_market', '-created_at']),
        ]


class RiskApprovalDecision(TimeStampedModel):
    linked_candidate = models.OneToOneField(RiskRuntimeCandidate, on_delete=models.CASCADE, related_name='approval_decision')
    approval_status = models.CharField(max_length=24, choices=RiskRuntimeApprovalStatus.choices)
    approval_rationale = models.TextField(blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    blockers = models.JSONField(default=list, blank=True)
    risk_score = models.DecimalField(max_digits=7, decimal_places=4, default=Decimal('0.0000'))
    max_allowed_exposure = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    watch_required = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['approval_status', '-created_at'])]


class RiskSizingPlan(TimeStampedModel):
    linked_candidate = models.ForeignKey(RiskRuntimeCandidate, on_delete=models.CASCADE, related_name='sizing_plans')
    linked_approval_decision = models.ForeignKey(RiskApprovalDecision, on_delete=models.CASCADE, related_name='sizing_plans')
    sizing_mode = models.CharField(max_length=32, choices=RiskRuntimeSizingMode.choices, default=RiskRuntimeSizingMode.NO_TRADE)
    raw_size_fraction = models.DecimalField(max_digits=8, decimal_places=6, default=Decimal('0.000000'))
    adjusted_size_fraction = models.DecimalField(max_digits=8, decimal_places=6, default=Decimal('0.000000'))
    cap_applied = models.BooleanField(default=False)
    cap_reason_codes = models.JSONField(default=list, blank=True)
    paper_notional_size = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    sizing_rationale = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class PositionWatchPlan(TimeStampedModel):
    linked_candidate = models.ForeignKey(RiskRuntimeCandidate, on_delete=models.CASCADE, related_name='watch_plans')
    linked_sizing_plan = models.ForeignKey(RiskSizingPlan, on_delete=models.CASCADE, related_name='watch_plans')
    watch_status = models.CharField(max_length=16, choices=PositionWatchPlanStatus.choices, default=PositionWatchPlanStatus.OPTIONAL)
    watch_triggers = models.JSONField(default=dict, blank=True)
    review_interval_hint = models.CharField(max_length=64, blank=True)
    escalation_path = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class RiskRuntimeRecommendation(TimeStampedModel):
    runtime_run = models.ForeignKey(RiskRuntimeRun, on_delete=models.CASCADE, related_name='recommendations')
    target_candidate = models.ForeignKey(
        RiskRuntimeCandidate,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='recommendations',
    )
    recommendation_type = models.CharField(max_length=64, choices=RiskRuntimeRecommendationType.choices)
    rationale = models.TextField(blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.DecimalField(max_digits=6, decimal_places=4, default=Decimal('0.0000'))
    blockers = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']

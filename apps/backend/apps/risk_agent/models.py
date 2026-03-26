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

from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.common.models import TimeStampedModel
from apps.markets.models import Market


class MockAgentRoleType(models.TextChoices):
    SCAN = 'SCAN', 'Scan'
    RESEARCH = 'RESEARCH', 'Research'
    PREDICTION = 'PREDICTION', 'Prediction'
    RISK = 'RISK', 'Risk'
    POSTMORTEM = 'POSTMORTEM', 'Postmortem'


class SignalDirection(models.TextChoices):
    BULLISH = 'BULLISH', 'Bullish'
    BEARISH = 'BEARISH', 'Bearish'
    NEUTRAL = 'NEUTRAL', 'Neutral'


class MarketSignalType(models.TextChoices):
    MOMENTUM = 'MOMENTUM', 'Momentum'
    MEAN_REVERSION = 'MEAN_REVERSION', 'Mean reversion'
    EXTREME = 'EXTREME', 'Extreme probability'
    OPPORTUNITY = 'OPPORTUNITY', 'Opportunity'
    RISK = 'RISK', 'Risk review'
    DORMANT = 'DORMANT', 'Dormant market'


class MarketSignalStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Active'
    MONITOR = 'MONITOR', 'Monitor'
    EXPIRED = 'EXPIRED', 'Expired'
    SUPERSEDED = 'SUPERSEDED', 'Superseded'


class SignalRunStatus(models.TextChoices):
    RUNNING = 'RUNNING', 'Running'
    COMPLETED = 'COMPLETED', 'Completed'
    FAILED = 'FAILED', 'Failed'


class MockAgent(TimeStampedModel):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=80, unique=True)
    description = models.TextField(blank=True)
    role_type = models.CharField(max_length=20, choices=MockAgentRoleType.choices)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self) -> str:
        return self.name


class SignalRun(TimeStampedModel):
    run_type = models.CharField(max_length=40, default='DEMO_SCAN')
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=SignalRunStatus.choices, default=SignalRunStatus.RUNNING)
    markets_evaluated = models.PositiveIntegerField(default=0)
    signals_created = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']

    def __str__(self) -> str:
        return f'{self.run_type} @ {self.started_at.isoformat()}'




class OpportunityStatus(models.TextChoices):
    WATCH = 'WATCH', 'Watch'
    CANDIDATE = 'CANDIDATE', 'Candidate'
    PROPOSAL_READY = 'PROPOSAL_READY', 'Proposal ready'
    BLOCKED = 'BLOCKED', 'Blocked'


class SignalFusionRun(TimeStampedModel):
    status = models.CharField(max_length=16, choices=SignalRunStatus.choices, default=SignalRunStatus.RUNNING)
    profile_slug = models.CharField(max_length=40, default='balanced_signal')
    triggered_by = models.CharField(max_length=40, default='manual_api')
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    markets_evaluated = models.PositiveIntegerField(default=0)
    signals_created = models.PositiveIntegerField(default=0)
    proposal_ready_count = models.PositiveIntegerField(default=0)
    blocked_count = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']


class OpportunitySignal(TimeStampedModel):
    run = models.ForeignKey(SignalFusionRun, on_delete=models.CASCADE, related_name='opportunities')
    market = models.ForeignKey(Market, on_delete=models.CASCADE, related_name='opportunity_signals')
    provider_slug = models.CharField(max_length=64, blank=True)
    research_score = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    triage_score = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    narrative_direction = models.CharField(max_length=20, blank=True)
    narrative_confidence = models.DecimalField(max_digits=7, decimal_places=4, default=Decimal('0.0000'))
    source_mix = models.CharField(max_length=24, default='none')
    prediction_system_probability = models.DecimalField(max_digits=7, decimal_places=4, null=True, blank=True)
    prediction_market_probability = models.DecimalField(max_digits=7, decimal_places=4, null=True, blank=True)
    edge = models.DecimalField(max_digits=8, decimal_places=4, default=Decimal('0.0000'))
    prediction_confidence = models.DecimalField(max_digits=7, decimal_places=4, default=Decimal('0.0000'))
    risk_level = models.CharField(max_length=12, default='MEDIUM')
    adjusted_quantity = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    runtime_constraints = models.JSONField(default=dict, blank=True)
    opportunity_score = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    opportunity_status = models.CharField(max_length=20, choices=OpportunityStatus.choices, default=OpportunityStatus.WATCH)
    rank = models.PositiveIntegerField(default=0)
    rationale = models.CharField(max_length=500, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['rank', '-opportunity_score', '-created_at', '-id']
        indexes = [
            models.Index(fields=['opportunity_status', '-opportunity_score']),
            models.Index(fields=['market', '-created_at']),
            models.Index(fields=['run', 'rank']),
        ]


class ProposalGateDecision(TimeStampedModel):
    opportunity = models.OneToOneField(OpportunitySignal, on_delete=models.CASCADE, related_name='proposal_gate')
    should_generate_proposal = models.BooleanField(default=False)
    proposal_priority = models.PositiveIntegerField(default=0)
    proposal_reason = models.CharField(max_length=255, blank=True)
    blocked_reason = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class MarketSignal(TimeStampedModel):
    market = models.ForeignKey(Market, on_delete=models.CASCADE, related_name='signals')
    agent = models.ForeignKey(MockAgent, on_delete=models.SET_NULL, related_name='signals', null=True, blank=True)
    run = models.ForeignKey(SignalRun, on_delete=models.SET_NULL, related_name='signals', null=True, blank=True)
    signal_type = models.CharField(max_length=24, choices=MarketSignalType.choices)
    status = models.CharField(max_length=16, choices=MarketSignalStatus.choices, default=MarketSignalStatus.ACTIVE)
    direction = models.CharField(max_length=12, choices=SignalDirection.choices, default=SignalDirection.NEUTRAL)
    score = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))])
    confidence = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('1.00'))])
    headline = models.CharField(max_length=255)
    thesis = models.TextField()
    rationale = models.TextField(blank=True)
    signal_probability = models.DecimalField(max_digits=7, decimal_places=4, null=True, blank=True)
    market_probability_at_signal = models.DecimalField(max_digits=7, decimal_places=4, null=True, blank=True)
    edge_estimate = models.DecimalField(max_digits=7, decimal_places=4, null=True, blank=True)
    is_actionable = models.BooleanField(default=False)
    expires_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['market', '-created_at']),
            models.Index(fields=['agent', 'status']),
            models.Index(fields=['signal_type', 'status']),
            models.Index(fields=['direction', 'is_actionable']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['market', 'agent', 'signal_type', 'status'],
                condition=models.Q(status__in=[MarketSignalStatus.ACTIVE, MarketSignalStatus.MONITOR]),
                name='signals_unique_live_signal_per_market_agent_type',
            ),
        ]

    def __str__(self) -> str:
        agent_slug = self.agent.slug if self.agent_id else 'aggregate'
        return f'{self.market.title} [{agent_slug}] {self.signal_type}'

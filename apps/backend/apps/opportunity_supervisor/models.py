from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel
from apps.markets.models import Market
from apps.operator_queue.models import OperatorQueueItem
from apps.paper_trading.models import PaperTrade
from apps.proposal_engine.models import TradeProposal


class OpportunityCycleStatus(models.TextChoices):
    RUNNING = 'RUNNING', 'Running'
    COMPLETED = 'COMPLETED', 'Completed'
    FAILED = 'FAILED', 'Failed'


class OpportunityExecutionPath(models.TextChoices):
    WATCH = 'WATCH', 'Watch'
    PROPOSAL_ONLY = 'PROPOSAL_ONLY', 'Proposal only'
    QUEUE = 'QUEUE', 'Queue'
    AUTO_EXECUTE_PAPER = 'AUTO_EXECUTE_PAPER', 'Auto execute paper'
    BLOCKED = 'BLOCKED', 'Blocked'


class OpportunityCycleRun(TimeStampedModel):
    status = models.CharField(max_length=16, choices=OpportunityCycleStatus.choices, default=OpportunityCycleStatus.RUNNING)
    profile_slug = models.CharField(max_length=64, blank=True)
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)
    markets_scanned = models.PositiveIntegerField(default=0)
    opportunities_built = models.PositiveIntegerField(default=0)
    proposals_generated = models.PositiveIntegerField(default=0)
    allocation_ready_count = models.PositiveIntegerField(default=0)
    queued_count = models.PositiveIntegerField(default=0)
    auto_executed_count = models.PositiveIntegerField(default=0)
    blocked_count = models.PositiveIntegerField(default=0)
    summary = models.CharField(max_length=255, blank=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']


class OpportunityCycleItem(TimeStampedModel):
    run = models.ForeignKey(OpportunityCycleRun, on_delete=models.CASCADE, related_name='items')
    market = models.ForeignKey(Market, on_delete=models.CASCADE, related_name='opportunity_cycle_items')
    source_provider = models.CharField(max_length=64, blank=True)
    research_context = models.JSONField(default=dict, blank=True)
    prediction_context = models.JSONField(default=dict, blank=True)
    risk_context = models.JSONField(default=dict, blank=True)
    signal_context = models.JSONField(default=dict, blank=True)
    proposal = models.ForeignKey(TradeProposal, null=True, blank=True, on_delete=models.SET_NULL, related_name='opportunity_cycle_items')
    proposal_status = models.CharField(max_length=32, blank=True)
    allocation_status = models.CharField(max_length=32, blank=True)
    allocation_quantity = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    execution_path = models.CharField(max_length=24, choices=OpportunityExecutionPath.choices, default=OpportunityExecutionPath.WATCH)
    rationale = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class OpportunityExecutionPlan(TimeStampedModel):
    item = models.OneToOneField(OpportunityCycleItem, on_delete=models.CASCADE, related_name='execution_plan')
    proposal = models.ForeignKey(TradeProposal, null=True, blank=True, on_delete=models.SET_NULL, related_name='execution_plans')
    queue_item = models.ForeignKey(OperatorQueueItem, null=True, blank=True, on_delete=models.SET_NULL, related_name='execution_plans')
    paper_trade = models.ForeignKey(PaperTrade, null=True, blank=True, on_delete=models.SET_NULL, related_name='execution_plans')
    allocation_quantity = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    runtime_mode = models.CharField(max_length=24, blank=True)
    policy_decision = models.CharField(max_length=24, blank=True)
    safety_status = models.CharField(max_length=24, blank=True)
    queue_required = models.BooleanField(default=False)
    auto_execute_allowed = models.BooleanField(default=False)
    final_recommended_action = models.CharField(max_length=24, choices=OpportunityExecutionPath.choices)
    explanation = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']

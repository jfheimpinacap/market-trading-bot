from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel
from apps.markets.models import Market
from apps.operator_queue.models import OperatorQueueItem
from apps.paper_trading.models import PaperTrade
from apps.prediction_agent.models import PredictionRuntimeAssessment
from apps.proposal_engine.models import TradeProposal
from apps.research_agent.models import MarketResearchCandidate
from apps.risk_agent.models import PositionWatchPlan, RiskApprovalDecision, RiskSizingPlan


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


class OpportunityFusionStatus(models.TextChoices):
    READY_FOR_PROPOSAL = 'READY_FOR_PROPOSAL', 'Ready for proposal'
    WATCH_ONLY = 'WATCH_ONLY', 'Watch only'
    BLOCKED_BY_RISK = 'BLOCKED_BY_RISK', 'Blocked by risk'
    BLOCKED_BY_LEARNING = 'BLOCKED_BY_LEARNING', 'Blocked by learning'
    LOW_CONVICTION = 'LOW_CONVICTION', 'Low conviction'
    NEEDS_REVIEW = 'NEEDS_REVIEW', 'Needs review'


class PaperOpportunityProposalStatus(models.TextChoices):
    PROPOSED = 'PROPOSED', 'Proposed'
    READY = 'READY', 'Ready'
    WATCH = 'WATCH', 'Watch'
    BLOCKED = 'BLOCKED', 'Blocked'
    SKIPPED = 'SKIPPED', 'Skipped'


class OpportunityRecommendationType(models.TextChoices):
    SEND_TO_PROPOSAL_ENGINE = 'SEND_TO_PROPOSAL_ENGINE', 'Send to proposal engine'
    SEND_TO_EXECUTION_SIMULATOR = 'SEND_TO_EXECUTION_SIMULATOR', 'Send to execution simulator'
    KEEP_ON_WATCH = 'KEEP_ON_WATCH', 'Keep on watch'
    BLOCK_BY_RISK = 'BLOCK_BY_RISK', 'Block by risk'
    BLOCK_BY_LEARNING = 'BLOCK_BY_LEARNING', 'Block by learning'
    BLOCK_LOW_CONVICTION = 'BLOCK_LOW_CONVICTION', 'Block low conviction'
    REQUIRE_MANUAL_OPPORTUNITY_REVIEW = 'REQUIRE_MANUAL_OPPORTUNITY_REVIEW', 'Require manual opportunity review'
    REORDER_OPPORTUNITY_PRIORITY = 'REORDER_OPPORTUNITY_PRIORITY', 'Reorder opportunity priority'


class OpportunityFusionCandidate(TimeStampedModel):
    runtime_run = models.ForeignKey('OpportunityCycleRuntimeRun', on_delete=models.CASCADE, related_name='candidates')
    linked_market = models.ForeignKey(Market, on_delete=models.CASCADE, related_name='opportunity_fusion_candidates')
    linked_research_candidate = models.ForeignKey(
        MarketResearchCandidate,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='opportunity_fusion_candidates',
    )
    linked_scan_signals = models.JSONField(default=list, blank=True)
    linked_prediction_assessment = models.ForeignKey(
        PredictionRuntimeAssessment,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='opportunity_fusion_candidates',
    )
    linked_risk_approval = models.ForeignKey(
        RiskApprovalDecision,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='opportunity_fusion_candidates',
    )
    linked_risk_sizing_plan = models.ForeignKey(
        RiskSizingPlan,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='opportunity_fusion_candidates',
    )
    linked_watch_plan = models.ForeignKey(
        PositionWatchPlan,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='opportunity_fusion_candidates',
    )
    linked_learning_adjustments = models.JSONField(default=list, blank=True)
    provider = models.CharField(max_length=64, blank=True)
    category = models.CharField(max_length=100, blank=True)
    market_probability = models.DecimalField(max_digits=7, decimal_places=4, null=True, blank=True)
    narrative_support_score = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    pursue_worthiness_score = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    adjusted_edge = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    confidence_score = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    risk_score = models.DecimalField(max_digits=7, decimal_places=4, null=True, blank=True)
    opportunity_quality_score = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-opportunity_quality_score', '-created_at', '-id']


class OpportunityCycleRuntimeRun(TimeStampedModel):
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    candidate_count = models.PositiveIntegerField(default=0)
    fused_count = models.PositiveIntegerField(default=0)
    ready_for_proposal_count = models.PositiveIntegerField(default=0)
    watch_count = models.PositiveIntegerField(default=0)
    blocked_count = models.PositiveIntegerField(default=0)
    sent_to_proposal_count = models.PositiveIntegerField(default=0)
    sent_to_execution_sim_context_count = models.PositiveIntegerField(default=0)
    recommendation_summary = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']


class OpportunityFusionAssessment(TimeStampedModel):
    runtime_run = models.ForeignKey(OpportunityCycleRuntimeRun, on_delete=models.CASCADE, related_name='assessments')
    linked_candidate = models.ForeignKey(OpportunityFusionCandidate, on_delete=models.CASCADE, related_name='assessments')
    fusion_status = models.CharField(max_length=32, choices=OpportunityFusionStatus.choices)
    conviction_score = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    execution_feasibility_score = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    learning_drag_score = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    portfolio_fit_score = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    final_opportunity_score = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    rationale = models.TextField(blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    blockers = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at_assessment = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-final_opportunity_score', '-created_at', '-id']


class PaperOpportunityProposal(TimeStampedModel):
    runtime_run = models.ForeignKey(OpportunityCycleRuntimeRun, on_delete=models.CASCADE, related_name='paper_proposals')
    linked_assessment = models.OneToOneField(OpportunityFusionAssessment, on_delete=models.CASCADE, related_name='paper_proposal')
    proposal = models.ForeignKey(TradeProposal, null=True, blank=True, on_delete=models.SET_NULL, related_name='opportunity_cycle_proposals')
    proposal_status = models.CharField(max_length=16, choices=PaperOpportunityProposalStatus.choices, default=PaperOpportunityProposalStatus.PROPOSED)
    recommended_direction = models.CharField(max_length=12, blank=True)
    calibrated_probability = models.DecimalField(max_digits=7, decimal_places=4, null=True, blank=True)
    adjusted_edge = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    approved_size_fraction = models.DecimalField(max_digits=8, decimal_places=6, null=True, blank=True)
    paper_notional_size = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    watch_required = models.BooleanField(default=False)
    execution_sim_recommended = models.BooleanField(default=False)
    rationale = models.TextField(blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    blockers = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at_proposal = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at', '-id']


class OpportunityRecommendation(TimeStampedModel):
    runtime_run = models.ForeignKey(OpportunityCycleRuntimeRun, on_delete=models.CASCADE, related_name='recommendations')
    target_assessment = models.ForeignKey(
        OpportunityFusionAssessment,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='recommendations',
    )
    recommendation_type = models.CharField(max_length=64, choices=OpportunityRecommendationType.choices)
    rationale = models.TextField(blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    blockers = models.JSONField(default=list, blank=True)
    created_at_recommendation = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at', '-id']

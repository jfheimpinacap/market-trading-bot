from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel


class AutonomousCycleMode(models.TextChoices):
    SCAN_TO_WATCH = 'SCAN_TO_WATCH', 'Scan to watch'
    SCAN_TO_PAPER_EXECUTION = 'SCAN_TO_PAPER_EXECUTION', 'Scan to paper execution'
    WATCH_ONLY = 'WATCH_ONLY', 'Watch only'
    FULL_AUTONOMOUS_PAPER_LOOP = 'FULL_AUTONOMOUS_PAPER_LOOP', 'Full autonomous paper loop'


class AutonomousCandidateStatus(models.TextChoices):
    WATCH = 'WATCH', 'Watch'
    EXECUTION_READY = 'EXECUTION_READY', 'Execution ready'
    BLOCKED = 'BLOCKED', 'Blocked'
    LOW_CONVICTION = 'LOW_CONVICTION', 'Low conviction'
    NEEDS_REVIEW = 'NEEDS_REVIEW', 'Needs review'


class AutonomousDecisionType(models.TextChoices):
    KEEP_ON_WATCH = 'KEEP_ON_WATCH', 'Keep on watch'
    EXECUTE_PAPER_TRADE = 'EXECUTE_PAPER_TRADE', 'Execute paper trade'
    BLOCK_BY_RISK = 'BLOCK_BY_RISK', 'Block by risk'
    BLOCK_BY_POLICY = 'BLOCK_BY_POLICY', 'Block by policy'
    BLOCK_BY_RUNTIME = 'BLOCK_BY_RUNTIME', 'Block by runtime'
    SKIP_LOW_EDGE = 'SKIP_LOW_EDGE', 'Skip low edge'
    SKIP_LOW_CONFIDENCE = 'SKIP_LOW_CONFIDENCE', 'Skip low confidence'
    SEND_TO_POSTMORTEM_ON_CLOSE = 'SEND_TO_POSTMORTEM_ON_CLOSE', 'Send to postmortem on close'


class AutonomousDecisionStatus(models.TextChoices):
    PROPOSED = 'PROPOSED', 'Proposed'
    EXECUTED = 'EXECUTED', 'Executed'
    SKIPPED = 'SKIPPED', 'Skipped'
    BLOCKED = 'BLOCKED', 'Blocked'


class AutonomousExecutionStatus(models.TextChoices):
    QUEUED = 'QUEUED', 'Queued'
    SUBMITTED = 'SUBMITTED', 'Submitted'
    FILLED = 'FILLED', 'Filled'
    PARTIAL = 'PARTIAL', 'Partial'
    NO_FILL = 'NO_FILL', 'No fill'
    CANCELLED = 'CANCELLED', 'Cancelled'
    SKIPPED = 'SKIPPED', 'Skipped'


class AutonomousWatchStatus(models.TextChoices):
    OPEN_MONITORING = 'OPEN_MONITORING', 'Open monitoring'
    REDUCE_SIGNAL = 'REDUCE_SIGNAL', 'Reduce signal'
    CLOSE_SIGNAL = 'CLOSE_SIGNAL', 'Close signal'
    HOLD_SIGNAL = 'HOLD_SIGNAL', 'Hold signal'
    EXIT_REVIEW_REQUIRED = 'EXIT_REVIEW_REQUIRED', 'Exit review required'
    CLOSED = 'CLOSED', 'Closed'


class AutonomousOutcomeType(models.TextChoices):
    PROFITABLE_EXIT = 'PROFITABLE_EXIT', 'Profitable exit'
    LOSS_EXIT = 'LOSS_EXIT', 'Loss exit'
    MANUAL_STOP = 'MANUAL_STOP', 'Manual stop'
    NO_ACTION = 'NO_ACTION', 'No action'
    EXPIRED_NO_TRADE = 'EXPIRED_NO_TRADE', 'Expired no trade'
    BLOCKED_PRE_TRADE = 'BLOCKED_PRE_TRADE', 'Blocked pre trade'


class AutonomousOutcomeStatus(models.TextChoices):
    OPEN = 'OPEN', 'Open'
    CLOSED = 'CLOSED', 'Closed'
    DEFERRED = 'DEFERRED', 'Deferred'


class AutonomousTradeCycleRun(TimeStampedModel):
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    cycle_mode = models.CharField(max_length=40, choices=AutonomousCycleMode.choices, default=AutonomousCycleMode.FULL_AUTONOMOUS_PAPER_LOOP)
    considered_candidate_count = models.PositiveIntegerField(default=0)
    watchlist_count = models.PositiveIntegerField(default=0)
    approved_for_execution_count = models.PositiveIntegerField(default=0)
    executed_paper_trade_count = models.PositiveIntegerField(default=0)
    blocked_count = models.PositiveIntegerField(default=0)
    closed_position_count = models.PositiveIntegerField(default=0)
    postmortem_handoff_count = models.PositiveIntegerField(default=0)
    recommendation_summary = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']


class AutonomousTradeCandidate(TimeStampedModel):
    cycle_run = models.ForeignKey(AutonomousTradeCycleRun, on_delete=models.CASCADE, related_name='candidates')
    linked_market = models.ForeignKey('markets.Market', on_delete=models.CASCADE, related_name='autonomous_trade_candidates')
    linked_scan_signal = models.ForeignKey('research_agent.NarrativeSignal', null=True, blank=True, on_delete=models.SET_NULL, related_name='autonomous_trade_candidates')
    linked_research_candidate = models.ForeignKey('research_agent.MarketResearchCandidate', null=True, blank=True, on_delete=models.SET_NULL, related_name='autonomous_trade_candidates')
    linked_prediction_recommendation = models.ForeignKey('prediction_agent.PredictionRuntimeRecommendation', null=True, blank=True, on_delete=models.SET_NULL, related_name='autonomous_trade_candidates')
    linked_risk_recommendation = models.ForeignKey('risk_agent.RiskRuntimeRecommendation', null=True, blank=True, on_delete=models.SET_NULL, related_name='autonomous_trade_candidates')
    linked_opportunity_signal = models.ForeignKey('opportunity_supervisor.OpportunityRecommendation', null=True, blank=True, on_delete=models.SET_NULL, related_name='autonomous_trade_candidates')
    candidate_status = models.CharField(max_length=24, choices=AutonomousCandidateStatus.choices, default=AutonomousCandidateStatus.NEEDS_REVIEW)
    system_probability = models.DecimalField(max_digits=7, decimal_places=4, null=True, blank=True)
    market_probability = models.DecimalField(max_digits=7, decimal_places=4, null=True, blank=True)
    adjusted_edge = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    confidence = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    risk_posture = models.CharField(max_length=32, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class AutonomousTradeDecision(TimeStampedModel):
    linked_candidate = models.ForeignKey(AutonomousTradeCandidate, on_delete=models.CASCADE, related_name='decisions')
    decision_type = models.CharField(max_length=40, choices=AutonomousDecisionType.choices)
    decision_status = models.CharField(max_length=16, choices=AutonomousDecisionStatus.choices, default=AutonomousDecisionStatus.PROPOSED)
    rationale = models.TextField(blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class AutonomousTradeExecution(TimeStampedModel):
    linked_candidate = models.ForeignKey(AutonomousTradeCandidate, on_delete=models.CASCADE, related_name='executions')
    linked_decision = models.ForeignKey(AutonomousTradeDecision, on_delete=models.CASCADE, related_name='executions')
    linked_paper_trade = models.ForeignKey('paper_trading.PaperTrade', null=True, blank=True, on_delete=models.SET_NULL, related_name='autonomous_trade_executions')
    execution_status = models.CharField(max_length=16, choices=AutonomousExecutionStatus.choices, default=AutonomousExecutionStatus.QUEUED)
    sizing_summary = models.CharField(max_length=255, blank=True)
    watch_plan_summary = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class AutonomousTradeWatchRecord(TimeStampedModel):
    linked_execution = models.ForeignKey(AutonomousTradeExecution, on_delete=models.CASCADE, related_name='watch_records')
    linked_position_watch_plan = models.ForeignKey('risk_agent.PositionWatchPlan', null=True, blank=True, on_delete=models.SET_NULL, related_name='autonomous_trade_watch_records')
    watch_status = models.CharField(max_length=24, choices=AutonomousWatchStatus.choices, default=AutonomousWatchStatus.OPEN_MONITORING)
    sentiment_shift_detected = models.BooleanField(default=False)
    market_move_detected = models.BooleanField(default=False)
    risk_change_detected = models.BooleanField(default=False)
    watch_notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class AutonomousTradeOutcome(TimeStampedModel):
    linked_execution = models.ForeignKey(AutonomousTradeExecution, on_delete=models.CASCADE, related_name='outcomes')
    linked_watch_record = models.ForeignKey(AutonomousTradeWatchRecord, null=True, blank=True, on_delete=models.SET_NULL, related_name='outcomes')
    outcome_type = models.CharField(max_length=24, choices=AutonomousOutcomeType.choices)
    outcome_status = models.CharField(max_length=16, choices=AutonomousOutcomeStatus.choices, default=AutonomousOutcomeStatus.OPEN)
    outcome_summary = models.CharField(max_length=255, blank=True)
    send_to_postmortem = models.BooleanField(default=False)
    send_to_learning = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']

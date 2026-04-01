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


class AutonomousOutcomeHandoffStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    EMITTED = 'EMITTED', 'Emitted'
    DUPLICATE_SKIPPED = 'DUPLICATE_SKIPPED', 'Duplicate skipped'
    BLOCKED = 'BLOCKED', 'Blocked'
    COMPLETED = 'COMPLETED', 'Completed'


class AutonomousPostmortemTriggerReason(models.TextChoices):
    LOSS_EXIT = 'LOSS_EXIT', 'Loss exit'
    EXIT_REVIEW_REQUIRED = 'EXIT_REVIEW_REQUIRED', 'Exit review required'
    RISK_DRIFT = 'RISK_DRIFT', 'Risk drift'
    SENTIMENT_REVERSAL = 'SENTIMENT_REVERSAL', 'Sentiment reversal'
    MANUAL_STOP = 'MANUAL_STOP', 'Manual stop'


class AutonomousLearningTriggerReason(models.TextChoices):
    LOSS_REVIEW_COMPLETED = 'LOSS_REVIEW_COMPLETED', 'Loss review completed'
    PROFITABLE_PATTERN_CAPTURE = 'PROFITABLE_PATTERN_CAPTURE', 'Profitable pattern capture'
    MONITORING_LESSON = 'MONITORING_LESSON', 'Monitoring lesson'
    NO_ACTION_LESSON = 'NO_ACTION_LESSON', 'No action lesson'


class AutonomousOutcomeHandoffRecommendationType(models.TextChoices):
    SEND_TO_POSTMORTEM_NOW = 'SEND_TO_POSTMORTEM_NOW', 'Send to postmortem now'
    WAIT_FOR_OUTCOME_CLOSURE = 'WAIT_FOR_OUTCOME_CLOSURE', 'Wait for outcome closure'
    SEND_TO_LEARNING_CAPTURE = 'SEND_TO_LEARNING_CAPTURE', 'Send to learning capture'
    BLOCK_DUPLICATE_HANDOFF = 'BLOCK_DUPLICATE_HANDOFF', 'Block duplicate handoff'
    REQUIRE_MANUAL_REVIEW_BEFORE_HANDOFF = 'REQUIRE_MANUAL_REVIEW_BEFORE_HANDOFF', 'Require manual review before handoff'
    CLOSE_FEEDBACK_LOOP = 'CLOSE_FEEDBACK_LOOP', 'Close feedback loop'


class AutonomousFeedbackRetrievalStatus(models.TextChoices):
    NO_RETRIEVAL = 'NO_RETRIEVAL', 'No retrieval'
    NO_HITS = 'NO_HITS', 'No hits'
    HITS_FOUND = 'HITS_FOUND', 'Hits found'
    BLOCKED = 'BLOCKED', 'Blocked'


class AutonomousFeedbackInfluenceType(models.TextChoices):
    CONTEXT_ONLY = 'CONTEXT_ONLY', 'Context only'
    CAUTION_BOOST = 'CAUTION_BOOST', 'Caution boost'
    CONFIDENCE_REDUCTION = 'CONFIDENCE_REDUCTION', 'Confidence reduction'
    WATCH_PRIORITY_UP = 'WATCH_PRIORITY_UP', 'Watch priority up'
    BLOCK_REPEAT_PATTERN = 'BLOCK_REPEAT_PATTERN', 'Block repeat pattern'
    RATIONALE_ENRICHMENT = 'RATIONALE_ENRICHMENT', 'Rationale enrichment'


class AutonomousFeedbackInfluenceStatus(models.TextChoices):
    SUGGESTED = 'SUGGESTED', 'Suggested'
    APPLIED = 'APPLIED', 'Applied'
    SKIPPED = 'SKIPPED', 'Skipped'
    BLOCKED = 'BLOCKED', 'Blocked'


class AutonomousFeedbackRecommendationType(models.TextChoices):
    APPLY_CAUTION_BOOST = 'APPLY_CAUTION_BOOST', 'Apply caution boost'
    REDUCE_CONFIDENCE_FOR_REPEAT_PATTERN = 'REDUCE_CONFIDENCE_FOR_REPEAT_PATTERN', 'Reduce confidence for repeat pattern'
    KEEP_ON_WATCH_WITH_MEMORY_CONTEXT = 'KEEP_ON_WATCH_WITH_MEMORY_CONTEXT', 'Keep on watch with memory context'
    BLOCK_REPEAT_LOSS_PATTERN = 'BLOCK_REPEAT_LOSS_PATTERN', 'Block repeat loss pattern'
    REQUIRE_MANUAL_REVIEW_FOR_MEMORY_CONFLICT = 'REQUIRE_MANUAL_REVIEW_FOR_MEMORY_CONFLICT', 'Require manual review for memory conflict'
    NO_RELEVANT_LEARNING_FOUND = 'NO_RELEVANT_LEARNING_FOUND', 'No relevant learning found'


class AutonomousSizingContextStatus(models.TextChoices):
    READY = 'READY', 'Ready'
    REDUCED = 'REDUCED', 'Reduced'
    BLOCKED = 'BLOCKED', 'Blocked'
    INSUFFICIENT_CONTEXT = 'INSUFFICIENT_CONTEXT', 'Insufficient context'


class AutonomousSizingMethod(models.TextChoices):
    FIXED_NOTIONAL = 'FIXED_NOTIONAL', 'Fixed notional'
    FRACTIONAL_KELLY = 'FRACTIONAL_KELLY', 'Fractional Kelly'
    KELLY_CAPPED = 'KELLY_CAPPED', 'Kelly capped'
    RISK_REDUCED_FRACTIONAL = 'RISK_REDUCED_FRACTIONAL', 'Risk reduced fractional'
    PORTFOLIO_THROTTLED = 'PORTFOLIO_THROTTLED', 'Portfolio throttled'


class AutonomousSizingDecisionStatus(models.TextChoices):
    PROPOSED = 'PROPOSED', 'Proposed'
    APPLIED = 'APPLIED', 'Applied'
    REDUCED = 'REDUCED', 'Reduced'
    BLOCKED = 'BLOCKED', 'Blocked'


class AutonomousSizingRecommendationType(models.TextChoices):
    APPLY_CAPPED_FRACTIONAL_KELLY = 'APPLY_CAPPED_FRACTIONAL_KELLY', 'Apply capped fractional Kelly'
    REDUCE_SIZE_FOR_LOW_CONFIDENCE = 'REDUCE_SIZE_FOR_LOW_CONFIDENCE', 'Reduce size for low confidence'
    REDUCE_SIZE_FOR_PORTFOLIO_PRESSURE = 'REDUCE_SIZE_FOR_PORTFOLIO_PRESSURE', 'Reduce size for portfolio pressure'
    BLOCK_SIZE_FOR_RISK_POSTURE = 'BLOCK_SIZE_FOR_RISK_POSTURE', 'Block size for risk posture'
    USE_MINIMAL_FIXED_NOTIONAL = 'USE_MINIMAL_FIXED_NOTIONAL', 'Use minimal fixed notional'
    REQUIRE_MANUAL_REVIEW_FOR_SIZING_CONFLICT = 'REQUIRE_MANUAL_REVIEW_FOR_SIZING_CONFLICT', 'Require manual review for sizing conflict'


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
    linked_sizing_decision = models.ForeignKey('autonomous_trader.AutonomousSizingDecision', null=True, blank=True, on_delete=models.SET_NULL, related_name='executions')
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


class AutonomousOutcomeHandoffRun(TimeStampedModel):
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    considered_outcome_count = models.PositiveIntegerField(default=0)
    eligible_postmortem_count = models.PositiveIntegerField(default=0)
    eligible_learning_count = models.PositiveIntegerField(default=0)
    postmortem_handoff_created_count = models.PositiveIntegerField(default=0)
    learning_handoff_created_count = models.PositiveIntegerField(default=0)
    duplicate_skipped_count = models.PositiveIntegerField(default=0)
    blocked_count = models.PositiveIntegerField(default=0)
    recommendation_summary = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']


class AutonomousPostmortemHandoff(TimeStampedModel):
    linked_outcome = models.ForeignKey(AutonomousTradeOutcome, on_delete=models.CASCADE, related_name='postmortem_handoffs')
    linked_execution = models.ForeignKey(AutonomousTradeExecution, null=True, blank=True, on_delete=models.SET_NULL, related_name='postmortem_handoffs')
    linked_candidate = models.ForeignKey(AutonomousTradeCandidate, null=True, blank=True, on_delete=models.SET_NULL, related_name='postmortem_handoffs')
    handoff_status = models.CharField(max_length=24, choices=AutonomousOutcomeHandoffStatus.choices, default=AutonomousOutcomeHandoffStatus.PENDING)
    trigger_reason = models.CharField(max_length=32, choices=AutonomousPostmortemTriggerReason.choices)
    linked_postmortem_run = models.ForeignKey('postmortem_agents.PostmortemBoardRun', null=True, blank=True, on_delete=models.SET_NULL, related_name='autonomous_handoffs')
    handoff_summary = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        constraints = [
            models.UniqueConstraint(fields=['linked_outcome', 'trigger_reason'], name='autonomous_unique_postmortem_handoff'),
        ]


class AutonomousLearningHandoff(TimeStampedModel):
    linked_outcome = models.ForeignKey(AutonomousTradeOutcome, on_delete=models.CASCADE, related_name='learning_handoffs')
    linked_postmortem_handoff = models.ForeignKey(AutonomousPostmortemHandoff, null=True, blank=True, on_delete=models.SET_NULL, related_name='learning_handoffs')
    handoff_status = models.CharField(max_length=24, choices=AutonomousOutcomeHandoffStatus.choices, default=AutonomousOutcomeHandoffStatus.PENDING)
    trigger_reason = models.CharField(max_length=40, choices=AutonomousLearningTriggerReason.choices)
    linked_learning_run = models.ForeignKey('learning_memory.PostmortemLearningRun', null=True, blank=True, on_delete=models.SET_NULL, related_name='autonomous_handoffs')
    handoff_summary = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        constraints = [
            models.UniqueConstraint(fields=['linked_outcome', 'trigger_reason'], name='autonomous_unique_learning_handoff'),
        ]


class AutonomousOutcomeHandoffRecommendation(TimeStampedModel):
    recommendation_type = models.CharField(max_length=48, choices=AutonomousOutcomeHandoffRecommendationType.choices)
    target_outcome = models.ForeignKey(AutonomousTradeOutcome, null=True, blank=True, on_delete=models.SET_NULL, related_name='handoff_recommendations')
    target_postmortem_handoff = models.ForeignKey(AutonomousPostmortemHandoff, null=True, blank=True, on_delete=models.SET_NULL, related_name='recommendations')
    target_learning_handoff = models.ForeignKey(AutonomousLearningHandoff, null=True, blank=True, on_delete=models.SET_NULL, related_name='recommendations')
    rationale = models.TextField(blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.DecimalField(max_digits=5, decimal_places=4, default=0.5)
    blockers = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class AutonomousFeedbackReuseRun(TimeStampedModel):
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    considered_candidate_count = models.PositiveIntegerField(default=0)
    retrieval_attempt_count = models.PositiveIntegerField(default=0)
    retrieval_hit_count = models.PositiveIntegerField(default=0)
    influence_applied_count = models.PositiveIntegerField(default=0)
    watch_caution_count = models.PositiveIntegerField(default=0)
    blocked_or_reduced_count = models.PositiveIntegerField(default=0)
    recommendation_summary = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']


class AutonomousFeedbackCandidateContext(TimeStampedModel):
    linked_reuse_run = models.ForeignKey(AutonomousFeedbackReuseRun, on_delete=models.CASCADE, related_name='candidate_contexts')
    linked_cycle_run = models.ForeignKey(AutonomousTradeCycleRun, on_delete=models.CASCADE, related_name='feedback_candidate_contexts')
    linked_candidate = models.ForeignKey(AutonomousTradeCandidate, on_delete=models.CASCADE, related_name='feedback_contexts')
    linked_execution = models.ForeignKey(AutonomousTradeExecution, null=True, blank=True, on_delete=models.SET_NULL, related_name='feedback_contexts')
    linked_market = models.ForeignKey('markets.Market', null=True, blank=True, on_delete=models.SET_NULL, related_name='autonomous_feedback_contexts')
    retrieval_status = models.CharField(max_length=20, choices=AutonomousFeedbackRetrievalStatus.choices, default=AutonomousFeedbackRetrievalStatus.NO_RETRIEVAL)
    top_precedent_count = models.PositiveIntegerField(default=0)
    top_failure_modes = models.JSONField(default=list, blank=True)
    top_lessons = models.JSONField(default=list, blank=True)
    context_summary = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class AutonomousFeedbackInfluenceRecord(TimeStampedModel):
    linked_candidate_context = models.ForeignKey(AutonomousFeedbackCandidateContext, on_delete=models.CASCADE, related_name='influence_records')
    linked_candidate = models.ForeignKey(AutonomousTradeCandidate, on_delete=models.CASCADE, related_name='feedback_influence_records')
    influence_type = models.CharField(max_length=32, choices=AutonomousFeedbackInfluenceType.choices)
    influence_status = models.CharField(max_length=16, choices=AutonomousFeedbackInfluenceStatus.choices, default=AutonomousFeedbackInfluenceStatus.SUGGESTED)
    influence_reason_codes = models.JSONField(default=list, blank=True)
    influence_summary = models.TextField(blank=True)
    pre_adjust_confidence = models.DecimalField(max_digits=7, decimal_places=4, null=True, blank=True)
    post_adjust_confidence = models.DecimalField(max_digits=7, decimal_places=4, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class AutonomousFeedbackRecommendation(TimeStampedModel):
    recommendation_type = models.CharField(max_length=64, choices=AutonomousFeedbackRecommendationType.choices)
    target_candidate = models.ForeignKey(AutonomousTradeCandidate, null=True, blank=True, on_delete=models.SET_NULL, related_name='feedback_recommendations')
    target_context = models.ForeignKey(AutonomousFeedbackCandidateContext, null=True, blank=True, on_delete=models.SET_NULL, related_name='recommendations')
    target_influence_record = models.ForeignKey(AutonomousFeedbackInfluenceRecord, null=True, blank=True, on_delete=models.SET_NULL, related_name='recommendations')
    rationale = models.TextField(blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.DecimalField(max_digits=5, decimal_places=4, default=0.5)
    blockers = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class AutonomousSizingRun(TimeStampedModel):
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    considered_candidate_count = models.PositiveIntegerField(default=0)
    approved_for_sizing_count = models.PositiveIntegerField(default=0)
    reduced_by_portfolio_count = models.PositiveIntegerField(default=0)
    reduced_by_risk_count = models.PositiveIntegerField(default=0)
    blocked_for_sizing_count = models.PositiveIntegerField(default=0)
    sized_for_execution_count = models.PositiveIntegerField(default=0)
    recommendation_summary = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']


class AutonomousSizingContext(TimeStampedModel):
    linked_run = models.ForeignKey(AutonomousSizingRun, on_delete=models.CASCADE, related_name='contexts')
    linked_cycle_run = models.ForeignKey(AutonomousTradeCycleRun, on_delete=models.CASCADE, related_name='sizing_contexts')
    linked_candidate = models.ForeignKey(AutonomousTradeCandidate, on_delete=models.CASCADE, related_name='sizing_contexts')
    linked_prediction_recommendation = models.ForeignKey('prediction_agent.PredictionRuntimeRecommendation', null=True, blank=True, on_delete=models.SET_NULL, related_name='autonomous_sizing_contexts')
    linked_risk_recommendation = models.ForeignKey('risk_agent.RiskRuntimeRecommendation', null=True, blank=True, on_delete=models.SET_NULL, related_name='autonomous_sizing_contexts')
    linked_portfolio_snapshot = models.ForeignKey('portfolio_governor.PortfolioExposureSnapshot', null=True, blank=True, on_delete=models.SET_NULL, related_name='autonomous_sizing_contexts')
    linked_feedback_influence = models.ForeignKey('autonomous_trader.AutonomousFeedbackInfluenceRecord', null=True, blank=True, on_delete=models.SET_NULL, related_name='sizing_contexts')
    linked_allocation_context = models.ForeignKey('allocation_engine.AllocationDecision', null=True, blank=True, on_delete=models.SET_NULL, related_name='autonomous_sizing_contexts')
    system_probability = models.DecimalField(max_digits=7, decimal_places=4, null=True, blank=True)
    market_probability = models.DecimalField(max_digits=7, decimal_places=4, null=True, blank=True)
    adjusted_edge = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    confidence = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    uncertainty = models.DecimalField(max_digits=7, decimal_places=4, null=True, blank=True)
    risk_posture = models.CharField(max_length=32, blank=True)
    portfolio_posture = models.CharField(max_length=32, blank=True)
    context_status = models.CharField(max_length=32, choices=AutonomousSizingContextStatus.choices, default=AutonomousSizingContextStatus.INSUFFICIENT_CONTEXT)
    context_summary = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class AutonomousSizingDecision(TimeStampedModel):
    linked_context = models.ForeignKey(AutonomousSizingContext, on_delete=models.CASCADE, related_name='sizing_decisions')
    linked_candidate = models.ForeignKey(AutonomousTradeCandidate, on_delete=models.CASCADE, related_name='sizing_decisions')
    sizing_method = models.CharField(max_length=40, choices=AutonomousSizingMethod.choices, default=AutonomousSizingMethod.FIXED_NOTIONAL)
    decision_status = models.CharField(max_length=16, choices=AutonomousSizingDecisionStatus.choices, default=AutonomousSizingDecisionStatus.PROPOSED)
    base_kelly_fraction = models.DecimalField(max_digits=8, decimal_places=6, null=True, blank=True)
    applied_fraction = models.DecimalField(max_digits=8, decimal_places=6, null=True, blank=True)
    notional_before_adjustment = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    notional_after_adjustment = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    final_paper_quantity = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    adjustment_reason_codes = models.JSONField(default=list, blank=True)
    decision_summary = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class AutonomousSizingRecommendation(TimeStampedModel):
    recommendation_type = models.CharField(max_length=64, choices=AutonomousSizingRecommendationType.choices)
    target_candidate = models.ForeignKey(AutonomousTradeCandidate, null=True, blank=True, on_delete=models.SET_NULL, related_name='sizing_recommendations')
    target_context = models.ForeignKey(AutonomousSizingContext, null=True, blank=True, on_delete=models.SET_NULL, related_name='recommendations')
    target_sizing_decision = models.ForeignKey(AutonomousSizingDecision, null=True, blank=True, on_delete=models.SET_NULL, related_name='recommendations')
    rationale = models.TextField(blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.DecimalField(max_digits=5, decimal_places=4, default=0.5)
    blockers = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']

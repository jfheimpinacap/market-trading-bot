from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel
from apps.continuous_demo.models import ContinuousDemoSession
from apps.semi_auto_demo.models import SemiAutoRun


class EvaluationRunStatus(models.TextChoices):
    READY = 'READY', 'Ready'
    IN_PROGRESS = 'IN_PROGRESS', 'In progress'
    FAILED = 'FAILED', 'Failed'


class EvaluationScope(models.TextChoices):
    SESSION = 'session', 'Session'
    RECENT_WINDOW = 'recent_window', 'Recent window'
    CUSTOM = 'custom', 'Custom'


class EvaluationMarketScope(models.TextChoices):
    DEMO_ONLY = 'demo_only', 'Demo only'
    REAL_ONLY = 'real_only', 'Real only'
    MIXED = 'mixed', 'Mixed'


class EvaluationRun(TimeStampedModel):
    related_continuous_session = models.ForeignKey(
        ContinuousDemoSession,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='evaluation_runs',
    )
    related_semi_auto_run = models.ForeignKey(
        SemiAutoRun,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='evaluation_runs',
    )
    evaluation_scope = models.CharField(max_length=24, choices=EvaluationScope.choices, default=EvaluationScope.SESSION)
    market_scope = models.CharField(max_length=16, choices=EvaluationMarketScope.choices, default=EvaluationMarketScope.MIXED)
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=EvaluationRunStatus.choices, default=EvaluationRunStatus.IN_PROGRESS)
    summary = models.CharField(max_length=255, blank=True)
    guidance = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']
        indexes = [
            models.Index(fields=['status', '-started_at']),
            models.Index(fields=['evaluation_scope', 'market_scope']),
        ]


class EvaluationMetricSet(TimeStampedModel):
    run = models.OneToOneField(EvaluationRun, on_delete=models.CASCADE, related_name='metric_set')
    cycles_count = models.PositiveIntegerField(default=0)
    proposals_generated = models.PositiveIntegerField(default=0)
    auto_executed_count = models.PositiveIntegerField(default=0)
    approval_required_count = models.PositiveIntegerField(default=0)
    blocked_count = models.PositiveIntegerField(default=0)
    pending_approvals_count = models.PositiveIntegerField(default=0)
    trades_executed_count = models.PositiveIntegerField(default=0)
    reviews_generated_count = models.PositiveIntegerField(default=0)
    favorable_reviews_count = models.PositiveIntegerField(default=0)
    neutral_reviews_count = models.PositiveIntegerField(default=0)
    unfavorable_reviews_count = models.PositiveIntegerField(default=0)
    approval_rate = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    block_rate = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    auto_execution_rate = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    favorable_review_rate = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    total_realized_pnl = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_unrealized_pnl = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_pnl = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    ending_equity = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    equity_delta = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    safety_events_count = models.PositiveIntegerField(default=0)
    cooldown_count = models.PositiveIntegerField(default=0)
    hard_stop_count = models.PositiveIntegerField(default=0)
    kill_switch_count = models.PositiveIntegerField(default=0)
    error_count = models.PositiveIntegerField(default=0)

    proposal_to_execution_ratio = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    execution_to_review_ratio = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    unfavorable_review_streak = models.PositiveIntegerField(default=0)
    average_pnl_per_trade = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    average_proposal_score = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    average_confidence = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    percent_real_market_trades = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    percent_demo_market_trades = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    percent_auto_approved = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    percent_manual_approved = models.DecimalField(max_digits=7, decimal_places=4, default=0)

    class Meta:
        ordering = ['-run__started_at', '-id']


class OutcomeResolution(models.TextChoices):
    YES = 'yes', 'Yes'
    NO = 'no', 'No'
    PARTIAL = 'partial', 'Partial'
    UNKNOWN = 'unknown', 'Unknown'


class OutcomeAlignmentStatus(models.TextChoices):
    WELL_CALIBRATED = 'WELL_CALIBRATED', 'Well calibrated'
    OVERCONFIDENT = 'OVERCONFIDENT', 'Overconfident'
    UNDERCONFIDENT = 'UNDERCONFIDENT', 'Underconfident'
    NO_EDGE_REALIZED = 'NO_EDGE_REALIZED', 'No edge realized'
    GOOD_SKIP = 'GOOD_SKIP', 'Good skip'
    BAD_SKIP = 'BAD_SKIP', 'Bad skip'
    NEEDS_REVIEW = 'NEEDS_REVIEW', 'Needs review'


class EvaluationSegmentScope(models.TextChoices):
    GLOBAL = 'global', 'Global'
    PROVIDER = 'provider', 'Provider'
    CATEGORY = 'category', 'Category'
    HORIZON_BAND = 'horizon_band', 'Horizon band'
    MODEL_MODE = 'model_mode', 'Model mode'


class EffectivenessMetricStatus(models.TextChoices):
    OK = 'OK', 'OK'
    CAUTION = 'CAUTION', 'Caution'
    POOR = 'POOR', 'Poor'
    NEEDS_MORE_DATA = 'NEEDS_MORE_DATA', 'Needs more data'


class EffectivenessMetricType(models.TextChoices):
    BRIER_SCORE = 'brier_score', 'Brier score'
    LOG_LOSS = 'log_loss', 'Log loss'
    CALIBRATION_ERROR = 'calibration_error', 'Calibration error'
    EDGE_CAPTURE_RATE = 'edge_capture_rate', 'Edge capture rate'
    SHORTLIST_CONVERSION_RATE = 'shortlist_conversion_rate', 'Shortlist conversion rate'
    PREDICTION_TO_RISK_PASS_RATE = 'prediction_to_risk_pass_rate', 'Prediction to risk pass rate'
    RISK_APPROVAL_PRECISION = 'risk_approval_precision', 'Risk approval precision'
    PROPOSAL_TO_EXECUTION_SIM_RATE = 'proposal_to_execution_sim_rate', 'Proposal to execution sim rate'
    WATCHLIST_HIT_RATE = 'watchlist_hit_rate', 'Watchlist hit rate'
    BLOCKED_OPPORTUNITY_ESCAPE_RATE = 'blocked_opportunity_escape_rate', 'Blocked opportunity escape rate'
    PROVIDER_BIAS_INDICATOR = 'provider_bias_indicator', 'Provider bias indicator'
    CATEGORY_BIAS_INDICATOR = 'category_bias_indicator', 'Category bias indicator'
    MODEL_MODE_DRIFT_INDICATOR = 'model_mode_drift_indicator', 'Model mode drift indicator'


class EvaluationRecommendationType(models.TextChoices):
    REVIEW_CALIBRATION_DRIFT = 'REVIEW_CALIBRATION_DRIFT', 'Review calibration drift'
    REVIEW_PROVIDER_BIAS = 'REVIEW_PROVIDER_BIAS', 'Review provider bias'
    REVIEW_CATEGORY_BIAS = 'REVIEW_CATEGORY_BIAS', 'Review category bias'
    TIGHTEN_RISK_GATE = 'TIGHTEN_RISK_GATE', 'Tighten risk gate'
    RELAX_RISK_GATE = 'RELAX_RISK_GATE', 'Relax risk gate'
    REQUIRE_MORE_DATA = 'REQUIRE_MORE_DATA', 'Require more data'
    INCREASE_MANUAL_REVIEW = 'INCREASE_MANUAL_REVIEW', 'Increase manual review'
    MONITOR_MODEL_MODE = 'MONITOR_MODEL_MODE', 'Monitor model mode'
    REORDER_EVALUATION_PRIORITY = 'REORDER_EVALUATION_PRIORITY', 'Reorder evaluation priority'


class EvaluationRuntimeRun(TimeStampedModel):
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    resolved_market_count = models.PositiveIntegerField(default=0)
    linked_prediction_count = models.PositiveIntegerField(default=0)
    linked_risk_count = models.PositiveIntegerField(default=0)
    linked_proposal_count = models.PositiveIntegerField(default=0)
    calibration_bucket_count = models.PositiveIntegerField(default=0)
    metric_count = models.PositiveIntegerField(default=0)
    drift_flag_count = models.PositiveIntegerField(default=0)
    recommendation_summary = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']


class OutcomeAlignmentRecord(TimeStampedModel):
    run = models.ForeignKey(EvaluationRuntimeRun, on_delete=models.CASCADE, related_name='outcome_alignment_records')
    linked_market = models.ForeignKey('markets.Market', on_delete=models.CASCADE, related_name='outcome_alignment_records')
    linked_prediction_assessment = models.ForeignKey(
        'prediction_agent.PredictionRuntimeAssessment', null=True, blank=True, on_delete=models.SET_NULL, related_name='outcome_alignment_records'
    )
    linked_risk_approval = models.ForeignKey(
        'risk_agent.RiskApprovalDecision', null=True, blank=True, on_delete=models.SET_NULL, related_name='outcome_alignment_records'
    )
    linked_opportunity_assessment = models.ForeignKey(
        'opportunity_supervisor.OpportunityFusionAssessment', null=True, blank=True, on_delete=models.SET_NULL, related_name='outcome_alignment_records'
    )
    linked_paper_proposal = models.ForeignKey(
        'opportunity_supervisor.PaperOpportunityProposal', null=True, blank=True, on_delete=models.SET_NULL, related_name='outcome_alignment_records'
    )
    resolved_outcome = models.CharField(max_length=16, choices=OutcomeResolution.choices, default=OutcomeResolution.UNKNOWN)
    market_probability_at_decision = models.DecimalField(max_digits=7, decimal_places=4, null=True, blank=True)
    system_probability_at_decision = models.DecimalField(max_digits=7, decimal_places=4, null=True, blank=True)
    calibrated_probability_at_decision = models.DecimalField(max_digits=7, decimal_places=4, null=True, blank=True)
    adjusted_edge_at_decision = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    risk_status_at_decision = models.CharField(max_length=24, blank=True)
    proposal_status_at_decision = models.CharField(max_length=24, blank=True)
    realized_result_score = models.DecimalField(max_digits=7, decimal_places=4, null=True, blank=True)
    alignment_status = models.CharField(max_length=32, choices=OutcomeAlignmentStatus.choices, default=OutcomeAlignmentStatus.NEEDS_REVIEW)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['run', '-created_at']),
            models.Index(fields=['alignment_status', '-created_at']),
        ]


class CalibrationBucket(TimeStampedModel):
    run = models.ForeignKey(EvaluationRuntimeRun, on_delete=models.CASCADE, related_name='calibration_buckets')
    bucket_label = models.CharField(max_length=24)
    sample_count = models.PositiveIntegerField(default=0)
    mean_predicted_probability = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    empirical_hit_rate = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    calibration_gap = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    brier_component = models.DecimalField(max_digits=7, decimal_places=4, null=True, blank=True)
    log_loss_component = models.DecimalField(max_digits=8, decimal_places=5, null=True, blank=True)
    segment_scope = models.CharField(max_length=24, choices=EvaluationSegmentScope.choices, default=EvaluationSegmentScope.GLOBAL)
    segment_value = models.CharField(max_length=120, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['segment_scope', 'segment_value', 'bucket_label', '-created_at']


class EffectivenessMetric(TimeStampedModel):
    run = models.ForeignKey(EvaluationRuntimeRun, on_delete=models.CASCADE, related_name='effectiveness_metrics')
    metric_type = models.CharField(max_length=48, choices=EffectivenessMetricType.choices)
    metric_scope = models.CharField(max_length=24, choices=EvaluationSegmentScope.choices, default=EvaluationSegmentScope.GLOBAL)
    metric_value = models.DecimalField(max_digits=10, decimal_places=6)
    sample_count = models.PositiveIntegerField(default=0)
    interpretation = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=24, choices=EffectivenessMetricStatus.choices, default=EffectivenessMetricStatus.NEEDS_MORE_DATA)
    reason_codes = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['metric_type', 'metric_scope', '-created_at']


class EvaluationRecommendation(TimeStampedModel):
    run = models.ForeignKey(EvaluationRuntimeRun, on_delete=models.CASCADE, related_name='recommendations')
    recommendation_type = models.CharField(max_length=48, choices=EvaluationRecommendationType.choices)
    target_metric = models.ForeignKey(
        EffectivenessMetric,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='recommendations',
    )
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    blockers = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']

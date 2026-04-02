from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel


class PortfolioThrottleState(models.TextChoices):
    NORMAL = 'NORMAL', 'Normal'
    CAUTION = 'CAUTION', 'Caution'
    THROTTLED = 'THROTTLED', 'Throttled'
    BLOCK_NEW_ENTRIES = 'BLOCK_NEW_ENTRIES', 'Block new entries'
    FORCE_REDUCE = 'FORCE_REDUCE', 'Force reduce'


class PortfolioExposureSnapshot(TimeStampedModel):
    total_equity = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    available_cash = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_exposure = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    open_positions = models.PositiveIntegerField(default=0)
    unrealized_pnl = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    recent_drawdown_pct = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    cash_reserve_ratio = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    concentration_market_ratio = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    concentration_provider_ratio = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    exposure_by_market = models.JSONField(default=list, blank=True)
    exposure_by_provider = models.JSONField(default=list, blank=True)
    exposure_by_category = models.JSONField(default=list, blank=True)
    created_at_snapshot = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at_snapshot', '-id']


class PortfolioThrottleDecision(TimeStampedModel):
    state = models.CharField(max_length=24, choices=PortfolioThrottleState.choices, default=PortfolioThrottleState.NORMAL)
    rationale = models.TextField(blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    recommended_max_new_positions = models.PositiveIntegerField(default=3)
    recommended_max_size_multiplier = models.DecimalField(max_digits=8, decimal_places=4, default=1)
    regime_signals = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at_decision = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at_decision', '-id']


class PortfolioGovernanceRunStatus(models.TextChoices):
    RUNNING = 'RUNNING', 'Running'
    COMPLETED = 'COMPLETED', 'Completed'
    FAILED = 'FAILED', 'Failed'


class PortfolioGovernanceRun(TimeStampedModel):
    status = models.CharField(max_length=16, choices=PortfolioGovernanceRunStatus.choices, default=PortfolioGovernanceRunStatus.RUNNING)
    profile_slug = models.CharField(max_length=64, blank=True)
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)
    exposure_snapshot = models.ForeignKey(PortfolioExposureSnapshot, null=True, blank=True, on_delete=models.SET_NULL, related_name='governance_runs')
    throttle_decision = models.ForeignKey(PortfolioThrottleDecision, null=True, blank=True, on_delete=models.SET_NULL, related_name='governance_runs')
    summary = models.CharField(max_length=255, blank=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']


class PortfolioExposureClusterType(models.TextChoices):
    MARKET = 'MARKET', 'Market'
    NARRATIVE = 'NARRATIVE', 'Narrative'
    DIRECTIONAL = 'DIRECTIONAL', 'Directional'
    THEMATIC = 'THEMATIC', 'Thematic'
    MIXED = 'MIXED', 'Mixed'


class PortfolioExposureNetDirection(models.TextChoices):
    LONG_BIAS = 'LONG_BIAS', 'Long bias'
    SHORT_BIAS = 'SHORT_BIAS', 'Short bias'
    MIXED = 'MIXED', 'Mixed'
    UNCLEAR = 'UNCLEAR', 'Unclear'


class PortfolioExposureRiskPressureState(models.TextChoices):
    NORMAL = 'NORMAL', 'Normal'
    CAUTION = 'CAUTION', 'Caution'
    THROTTLED = 'THROTTLED', 'Throttled'
    BLOCK_NEW_EXPOSURE = 'BLOCK_NEW_EXPOSURE', 'Block new exposure'


class PortfolioExposureConcentrationStatus(models.TextChoices):
    NORMAL = 'NORMAL', 'Normal'
    ELEVATED = 'ELEVATED', 'Elevated'
    HIGH = 'HIGH', 'High'
    CRITICAL = 'CRITICAL', 'Critical'


class SessionExposureContributionRole(models.TextChoices):
    PRIMARY_DRIVER = 'PRIMARY_DRIVER', 'Primary driver'
    SUPPORTING = 'SUPPORTING', 'Supporting'
    REDUNDANT = 'REDUNDANT', 'Redundant'
    CONFLICTING = 'CONFLICTING', 'Conflicting'
    LOW_VALUE = 'LOW_VALUE', 'Low value'


class SessionExposureContributionDirection(models.TextChoices):
    LONG = 'LONG', 'Long'
    SHORT = 'SHORT', 'Short'
    MIXED = 'MIXED', 'Mixed'
    NEUTRAL = 'NEUTRAL', 'Neutral'


class SessionExposureContributionStrength(models.TextChoices):
    HIGH = 'HIGH', 'High'
    MEDIUM = 'MEDIUM', 'Medium'
    LOW = 'LOW', 'Low'


class PortfolioExposureConflictReviewType(models.TextChoices):
    CONCENTRATION_RISK = 'CONCENTRATION_RISK', 'Concentration risk'
    REDUNDANT_SESSION_STACKING = 'REDUNDANT_SESSION_STACKING', 'Redundant session stacking'
    DIRECTIONAL_CONFLICT = 'DIRECTIONAL_CONFLICT', 'Directional conflict'
    PENDING_DISPATCH_OVERLOAD = 'PENDING_DISPATCH_OVERLOAD', 'Pending dispatch overload'
    LOW_VALUE_CAPACITY_WASTE = 'LOW_VALUE_CAPACITY_WASTE', 'Low value capacity waste'
    PORTFOLIO_PRESSURE_CONFLICT = 'PORTFOLIO_PRESSURE_CONFLICT', 'Portfolio pressure conflict'


class PortfolioExposureConflictReviewSeverity(models.TextChoices):
    INFO = 'INFO', 'Info'
    CAUTION = 'CAUTION', 'Caution'
    HIGH = 'HIGH', 'High'
    CRITICAL = 'CRITICAL', 'Critical'


class PortfolioExposureDecisionType(models.TextChoices):
    KEEP_EXPOSURE_AS_IS = 'KEEP_EXPOSURE_AS_IS', 'Keep exposure as is'
    THROTTLE_NEW_ENTRIES = 'THROTTLE_NEW_ENTRIES', 'Throttle new entries'
    DEFER_PENDING_DISPATCH = 'DEFER_PENDING_DISPATCH', 'Defer pending dispatch'
    PARK_WEAKER_SESSION = 'PARK_WEAKER_SESSION', 'Park weaker session'
    PAUSE_CLUSTER_ACTIVITY = 'PAUSE_CLUSTER_ACTIVITY', 'Pause cluster activity'
    REDUCE_EXPOSURE_PRIORITY = 'REDUCE_EXPOSURE_PRIORITY', 'Reduce exposure priority'
    REQUIRE_MANUAL_EXPOSURE_REVIEW = 'REQUIRE_MANUAL_EXPOSURE_REVIEW', 'Require manual exposure review'


class PortfolioExposureDecisionStatus(models.TextChoices):
    PROPOSED = 'PROPOSED', 'Proposed'
    APPLIED = 'APPLIED', 'Applied'
    SKIPPED = 'SKIPPED', 'Skipped'
    BLOCKED = 'BLOCKED', 'Blocked'


class PortfolioExposureRecommendationType(models.TextChoices):
    KEEP_CURRENT_EXPOSURE = 'KEEP_CURRENT_EXPOSURE', 'Keep current exposure'
    THROTTLE_CLUSTER_FOR_CONCENTRATION = 'THROTTLE_CLUSTER_FOR_CONCENTRATION', 'Throttle cluster for concentration'
    DEFER_WEAKER_PENDING_DISPATCH = 'DEFER_WEAKER_PENDING_DISPATCH', 'Defer weaker pending dispatch'
    PARK_REDUNDANT_SESSION = 'PARK_REDUNDANT_SESSION', 'Park redundant session'
    PAUSE_CLUSTER_FOR_PORTFOLIO_PRESSURE = 'PAUSE_CLUSTER_FOR_PORTFOLIO_PRESSURE', 'Pause cluster for portfolio pressure'
    REQUIRE_MANUAL_EXPOSURE_REVIEW = 'REQUIRE_MANUAL_EXPOSURE_REVIEW', 'Require manual exposure review'


class PortfolioExposureCoordinationRun(TimeStampedModel):
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    considered_cluster_count = models.PositiveIntegerField(default=0)
    concentration_alert_count = models.PositiveIntegerField(default=0)
    conflict_alert_count = models.PositiveIntegerField(default=0)
    throttle_count = models.PositiveIntegerField(default=0)
    defer_count = models.PositiveIntegerField(default=0)
    park_count = models.PositiveIntegerField(default=0)
    manual_review_count = models.PositiveIntegerField(default=0)
    recommendation_summary = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']


class PortfolioExposureClusterSnapshot(TimeStampedModel):
    linked_run = models.ForeignKey(PortfolioExposureCoordinationRun, on_delete=models.CASCADE, related_name='cluster_snapshots')
    cluster_label = models.CharField(max_length=140)
    cluster_type = models.CharField(max_length=16, choices=PortfolioExposureClusterType.choices, default=PortfolioExposureClusterType.MIXED)
    linked_market = models.ForeignKey('markets.Market', null=True, blank=True, on_delete=models.SET_NULL, related_name='portfolio_exposure_clusters')
    net_direction = models.CharField(max_length=16, choices=PortfolioExposureNetDirection.choices, default=PortfolioExposureNetDirection.UNCLEAR)
    session_count = models.PositiveIntegerField(default=0)
    open_position_count = models.PositiveIntegerField(default=0)
    pending_dispatch_count = models.PositiveIntegerField(default=0)
    aggregate_notional_pressure = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    aggregate_risk_pressure_state = models.CharField(max_length=20, choices=PortfolioExposureRiskPressureState.choices, default=PortfolioExposureRiskPressureState.NORMAL)
    concentration_status = models.CharField(max_length=16, choices=PortfolioExposureConcentrationStatus.choices, default=PortfolioExposureConcentrationStatus.NORMAL)
    cluster_summary = models.CharField(max_length=255, blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at_snapshot = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at_snapshot', '-id']


class SessionExposureContribution(TimeStampedModel):
    linked_session = models.ForeignKey('mission_control.AutonomousRuntimeSession', on_delete=models.CASCADE, related_name='portfolio_exposure_contributions')
    linked_cluster_snapshot = models.ForeignKey(PortfolioExposureClusterSnapshot, on_delete=models.CASCADE, related_name='session_contributions')
    linked_admission_decision = models.ForeignKey(
        'mission_control.AutonomousSessionAdmissionDecision',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='portfolio_exposure_contributions',
    )
    linked_dispatch_record = models.ForeignKey(
        'autonomous_trader.AutonomousDispatchRecord',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='session_exposure_contributions',
    )
    linked_trade_execution = models.ForeignKey(
        'autonomous_trader.AutonomousTradeExecution',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='session_exposure_contributions',
    )
    contribution_role = models.CharField(max_length=20, choices=SessionExposureContributionRole.choices, default=SessionExposureContributionRole.SUPPORTING)
    contribution_direction = models.CharField(max_length=12, choices=SessionExposureContributionDirection.choices, default=SessionExposureContributionDirection.NEUTRAL)
    contribution_strength = models.CharField(max_length=8, choices=SessionExposureContributionStrength.choices, default=SessionExposureContributionStrength.LOW)
    contribution_summary = models.CharField(max_length=255, blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at_snapshot = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at_snapshot', '-id']


class PortfolioExposureConflictReview(TimeStampedModel):
    linked_cluster_snapshot = models.ForeignKey(PortfolioExposureClusterSnapshot, on_delete=models.CASCADE, related_name='conflict_reviews')
    review_type = models.CharField(max_length=36, choices=PortfolioExposureConflictReviewType.choices)
    review_severity = models.CharField(max_length=12, choices=PortfolioExposureConflictReviewSeverity.choices, default=PortfolioExposureConflictReviewSeverity.INFO)
    review_summary = models.CharField(max_length=255, blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at_review = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at_review', '-id']


class PortfolioExposureDecision(TimeStampedModel):
    linked_cluster_snapshot = models.ForeignKey(PortfolioExposureClusterSnapshot, on_delete=models.CASCADE, related_name='decisions')
    linked_conflict_review = models.ForeignKey(PortfolioExposureConflictReview, null=True, blank=True, on_delete=models.SET_NULL, related_name='decisions')
    decision_type = models.CharField(max_length=36, choices=PortfolioExposureDecisionType.choices)
    decision_status = models.CharField(max_length=12, choices=PortfolioExposureDecisionStatus.choices, default=PortfolioExposureDecisionStatus.PROPOSED)
    auto_applicable = models.BooleanField(default=False)
    decision_summary = models.CharField(max_length=255, blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at_decision = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at_decision', '-id']


class PortfolioExposureRecommendation(TimeStampedModel):
    recommendation_type = models.CharField(max_length=48, choices=PortfolioExposureRecommendationType.choices)
    target_cluster_snapshot = models.ForeignKey(PortfolioExposureClusterSnapshot, null=True, blank=True, on_delete=models.SET_NULL, related_name='recommendations')
    target_conflict_review = models.ForeignKey(PortfolioExposureConflictReview, null=True, blank=True, on_delete=models.SET_NULL, related_name='recommendations')
    target_exposure_decision = models.ForeignKey(PortfolioExposureDecision, null=True, blank=True, on_delete=models.SET_NULL, related_name='recommendations')
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.FloatField(default=0.5)
    blockers = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class PortfolioExposureApplyTargetType(models.TextChoices):
    SESSION = 'SESSION', 'Session'
    PENDING_DISPATCH = 'PENDING_DISPATCH', 'Pending dispatch'
    CLUSTER_GATE = 'CLUSTER_GATE', 'Cluster gate'
    ADMISSION_PATH = 'ADMISSION_PATH', 'Admission path'


class PortfolioExposureApplyTargetStatus(models.TextChoices):
    READY = 'READY', 'Ready'
    APPLIED = 'APPLIED', 'Applied'
    SKIPPED = 'SKIPPED', 'Skipped'
    BLOCKED = 'BLOCKED', 'Blocked'


class PortfolioExposureApplyType(models.TextChoices):
    APPLY_THROTTLE_NEW_ENTRIES = 'APPLY_THROTTLE_NEW_ENTRIES', 'Apply throttle new entries'
    APPLY_DEFER_PENDING_DISPATCH = 'APPLY_DEFER_PENDING_DISPATCH', 'Apply defer pending dispatch'
    APPLY_PARK_SESSION = 'APPLY_PARK_SESSION', 'Apply park session'
    APPLY_PAUSE_CLUSTER_ACTIVITY = 'APPLY_PAUSE_CLUSTER_ACTIVITY', 'Apply pause cluster activity'
    APPLY_MANUAL_REVIEW_ONLY = 'APPLY_MANUAL_REVIEW_ONLY', 'Apply manual review only'
    APPLY_NO_CHANGE = 'APPLY_NO_CHANGE', 'Apply no change'


class PortfolioExposureApplyDecisionStatus(models.TextChoices):
    PROPOSED = 'PROPOSED', 'Proposed'
    APPLIED = 'APPLIED', 'Applied'
    SKIPPED = 'SKIPPED', 'Skipped'
    BLOCKED = 'BLOCKED', 'Blocked'
    FAILED = 'FAILED', 'Failed'


class PortfolioExposureApplyRecordStatus(models.TextChoices):
    APPLIED = 'APPLIED', 'Applied'
    SKIPPED = 'SKIPPED', 'Skipped'
    BLOCKED = 'BLOCKED', 'Blocked'
    FAILED = 'FAILED', 'Failed'


class PortfolioExposureApplyEffectType(models.TextChoices):
    NEW_ENTRIES_THROTTLED = 'NEW_ENTRIES_THROTTLED', 'New entries throttled'
    DISPATCH_DEFERRED = 'DISPATCH_DEFERRED', 'Dispatch deferred'
    SESSION_PARKED = 'SESSION_PARKED', 'Session parked'
    CLUSTER_ACTIVITY_PAUSED = 'CLUSTER_ACTIVITY_PAUSED', 'Cluster activity paused'
    MANUAL_REVIEW_ONLY = 'MANUAL_REVIEW_ONLY', 'Manual review only'
    NO_CHANGE = 'NO_CHANGE', 'No change'


class PortfolioExposureApplyRecommendationType(models.TextChoices):
    APPLY_CLUSTER_THROTTLE_NOW = 'APPLY_CLUSTER_THROTTLE_NOW', 'Apply cluster throttle now'
    DEFER_PENDING_DISPATCH_SAFELY = 'DEFER_PENDING_DISPATCH_SAFELY', 'Defer pending dispatch safely'
    PARK_REDUNDANT_SESSION_NOW = 'PARK_REDUNDANT_SESSION_NOW', 'Park redundant session now'
    PAUSE_CLUSTER_ACTIVITY_CONSERVATIVELY = 'PAUSE_CLUSTER_ACTIVITY_CONSERVATIVELY', 'Pause cluster activity conservatively'
    REQUIRE_MANUAL_EXPOSURE_APPLY_REVIEW = 'REQUIRE_MANUAL_EXPOSURE_APPLY_REVIEW', 'Require manual exposure apply review'
    LEAVE_EXPOSURE_DECISION_AS_ADVISORY_ONLY = 'LEAVE_EXPOSURE_DECISION_AS_ADVISORY_ONLY', 'Leave exposure decision as advisory only'


class PortfolioExposureApplyRun(TimeStampedModel):
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    considered_decision_count = models.PositiveIntegerField(default=0)
    applied_count = models.PositiveIntegerField(default=0)
    skipped_count = models.PositiveIntegerField(default=0)
    blocked_count = models.PositiveIntegerField(default=0)
    deferred_dispatch_apply_count = models.PositiveIntegerField(default=0)
    parked_session_apply_count = models.PositiveIntegerField(default=0)
    paused_cluster_apply_count = models.PositiveIntegerField(default=0)
    recommendation_summary = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']


class PortfolioExposureApplyTarget(TimeStampedModel):
    linked_apply_run = models.ForeignKey(PortfolioExposureApplyRun, on_delete=models.CASCADE, related_name='targets')
    linked_exposure_decision = models.ForeignKey(PortfolioExposureDecision, on_delete=models.CASCADE, related_name='apply_targets')
    target_type = models.CharField(max_length=24, choices=PortfolioExposureApplyTargetType.choices)
    linked_session = models.ForeignKey('mission_control.AutonomousRuntimeSession', null=True, blank=True, on_delete=models.SET_NULL, related_name='portfolio_exposure_apply_targets')
    linked_dispatch_record = models.ForeignKey('autonomous_trader.AutonomousDispatchRecord', null=True, blank=True, on_delete=models.SET_NULL, related_name='portfolio_exposure_apply_targets')
    linked_cluster_snapshot = models.ForeignKey(PortfolioExposureClusterSnapshot, null=True, blank=True, on_delete=models.SET_NULL, related_name='apply_targets')
    target_status = models.CharField(max_length=12, choices=PortfolioExposureApplyTargetStatus.choices, default=PortfolioExposureApplyTargetStatus.READY)
    target_summary = models.CharField(max_length=255, blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at_target = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at_target', '-id']


class PortfolioExposureApplyDecision(TimeStampedModel):
    linked_apply_run = models.ForeignKey(PortfolioExposureApplyRun, on_delete=models.CASCADE, related_name='apply_decisions')
    linked_exposure_decision = models.ForeignKey(PortfolioExposureDecision, on_delete=models.CASCADE, related_name='apply_decisions')
    apply_type = models.CharField(max_length=40, choices=PortfolioExposureApplyType.choices)
    apply_status = models.CharField(max_length=12, choices=PortfolioExposureApplyDecisionStatus.choices, default=PortfolioExposureApplyDecisionStatus.PROPOSED)
    auto_applicable = models.BooleanField(default=False)
    apply_summary = models.CharField(max_length=255, blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at_decision = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at_decision', '-id']


class PortfolioExposureApplyRecord(TimeStampedModel):
    linked_apply_decision = models.ForeignKey(PortfolioExposureApplyDecision, on_delete=models.CASCADE, related_name='records')
    record_status = models.CharField(max_length=12, choices=PortfolioExposureApplyRecordStatus.choices)
    effect_type = models.CharField(max_length=32, choices=PortfolioExposureApplyEffectType.choices)
    record_summary = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at_record = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at_record', '-id']


class PortfolioExposureApplyRecommendation(TimeStampedModel):
    recommendation_type = models.CharField(max_length=56, choices=PortfolioExposureApplyRecommendationType.choices)
    target_exposure_decision = models.ForeignKey(PortfolioExposureDecision, null=True, blank=True, on_delete=models.SET_NULL, related_name='apply_recommendations')
    target_apply_decision = models.ForeignKey(PortfolioExposureApplyDecision, null=True, blank=True, on_delete=models.SET_NULL, related_name='recommendations')
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.FloatField(default=0.5)
    blockers = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']

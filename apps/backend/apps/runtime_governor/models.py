from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel


class RuntimeMode(models.TextChoices):
    OBSERVE_ONLY = 'OBSERVE_ONLY', 'Observe only'
    PAPER_ASSIST = 'PAPER_ASSIST', 'Paper assist'
    PAPER_SEMI_AUTO = 'PAPER_SEMI_AUTO', 'Paper semi auto'
    PAPER_AUTO = 'PAPER_AUTO', 'Paper auto'


class RuntimeStateStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Active'
    DEGRADED = 'DEGRADED', 'Degraded'
    PAUSED = 'PAUSED', 'Paused'
    STOPPED = 'STOPPED', 'Stopped'


class RuntimeSetBy(models.TextChoices):
    MANUAL = 'manual', 'Manual'
    OPERATOR = 'operator', 'Operator'
    READINESS = 'readiness', 'Readiness'
    SAFETY = 'safety', 'Safety'
    SYSTEM = 'system', 'System'


class RuntimeModeProfile(TimeStampedModel):
    mode = models.CharField(max_length=24, choices=RuntimeMode.choices, unique=True)
    label = models.CharField(max_length=48)
    description = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    allow_signal_generation = models.BooleanField(default=True)
    allow_proposals = models.BooleanField(default=True)
    allow_allocation = models.BooleanField(default=True)
    allow_real_market_ops = models.BooleanField(default=False)
    allow_auto_execution = models.BooleanField(default=False)
    allow_continuous_loop = models.BooleanField(default=False)
    require_operator_for_all_trades = models.BooleanField(default=True)
    allow_pending_approvals = models.BooleanField(default=True)
    allow_replay = models.BooleanField(default=True)
    allow_experiments = models.BooleanField(default=True)

    max_auto_trades_per_cycle = models.PositiveIntegerField(default=0)
    max_auto_trades_per_session = models.PositiveIntegerField(default=0)
    stricter_safety_overrides = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['mode']


class RuntimeModeState(TimeStampedModel):
    current_mode = models.CharField(max_length=24, choices=RuntimeMode.choices, default=RuntimeMode.OBSERVE_ONLY)
    desired_mode = models.CharField(max_length=24, choices=RuntimeMode.choices, null=True, blank=True)
    status = models.CharField(max_length=12, choices=RuntimeStateStatus.choices, default=RuntimeStateStatus.ACTIVE)
    set_by = models.CharField(max_length=16, choices=RuntimeSetBy.choices, default=RuntimeSetBy.MANUAL)
    rationale = models.CharField(max_length=255, blank=True)
    effective_at = models.DateTimeField(default=timezone.now)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['id']


class RuntimeTransitionLog(TimeStampedModel):
    from_mode = models.CharField(max_length=24, choices=RuntimeMode.choices, null=True, blank=True)
    to_mode = models.CharField(max_length=24, choices=RuntimeMode.choices)
    from_status = models.CharField(max_length=12, choices=RuntimeStateStatus.choices, null=True, blank=True)
    to_status = models.CharField(max_length=12, choices=RuntimeStateStatus.choices, default=RuntimeStateStatus.ACTIVE)
    trigger_source = models.CharField(max_length=32, choices=RuntimeSetBy.choices, default=RuntimeSetBy.SYSTEM)
    reason = models.CharField(max_length=255)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['trigger_source', '-created_at']),
            models.Index(fields=['to_mode', '-created_at']),
        ]


class ExposurePressureState(models.TextChoices):
    NORMAL = 'NORMAL', 'Normal'
    CAUTION = 'CAUTION', 'Caution'
    THROTTLED = 'THROTTLED', 'Throttled'
    BLOCK_NEW_ACTIVITY = 'BLOCK_NEW_ACTIVITY', 'Block new activity'


class AdmissionPressureState(models.TextChoices):
    NORMAL = 'NORMAL', 'Normal'
    CAUTION = 'CAUTION', 'Caution'
    THROTTLED = 'THROTTLED', 'Throttled'
    BLOCKED = 'BLOCKED', 'Blocked'


class SessionHealthState(models.TextChoices):
    HEALTHY = 'HEALTHY', 'Healthy'
    CAUTION = 'CAUTION', 'Caution'
    DEGRADED = 'DEGRADED', 'Degraded'
    BLOCKED = 'BLOCKED', 'Blocked'


class RecentLossState(models.TextChoices):
    NONE = 'NONE', 'None'
    RECENT_LOSS = 'RECENT_LOSS', 'Recent loss'
    REPEATED_LOSS = 'REPEATED_LOSS', 'Repeated loss'


class SignalQualityState(models.TextChoices):
    STRONG = 'STRONG', 'Strong'
    NORMAL = 'NORMAL', 'Normal'
    WEAK = 'WEAK', 'Weak'
    QUIET = 'QUIET', 'Quiet'


class RuntimePostureState(models.TextChoices):
    NORMAL = 'NORMAL', 'Normal'
    CAUTION = 'CAUTION', 'Caution'
    BLOCKED = 'BLOCKED', 'Blocked'


class SafetyPostureState(models.TextChoices):
    NORMAL = 'NORMAL', 'Normal'
    CAUTION = 'CAUTION', 'Caution'
    HARD_BLOCK = 'HARD_BLOCK', 'Hard block'


class IncidentPressureState(models.TextChoices):
    NONE = 'NONE', 'None'
    CAUTION = 'CAUTION', 'Caution'
    HIGH = 'HIGH', 'High'


class PortfolioPressureState(models.TextChoices):
    NORMAL = 'NORMAL', 'Normal'
    CAUTION = 'CAUTION', 'Caution'
    THROTTLED = 'THROTTLED', 'Throttled'
    BLOCK_NEW_ENTRIES = 'BLOCK_NEW_ENTRIES', 'Block new entries'


class GlobalOperatingMode(models.TextChoices):
    BALANCED = 'BALANCED', 'Balanced'
    CAUTION = 'CAUTION', 'Caution'
    MONITOR_ONLY = 'MONITOR_ONLY', 'Monitor only'
    RECOVERY_MODE = 'RECOVERY_MODE', 'Recovery mode'
    THROTTLED = 'THROTTLED', 'Throttled'
    BLOCKED = 'BLOCKED', 'Blocked'


class GlobalOperatingModeDecisionType(models.TextChoices):
    KEEP_CURRENT_MODE = 'KEEP_CURRENT_MODE', 'Keep current mode'
    SWITCH_TO_CAUTION = 'SWITCH_TO_CAUTION', 'Switch to caution'
    SWITCH_TO_MONITOR_ONLY = 'SWITCH_TO_MONITOR_ONLY', 'Switch to monitor only'
    SWITCH_TO_RECOVERY_MODE = 'SWITCH_TO_RECOVERY_MODE', 'Switch to recovery mode'
    SWITCH_TO_THROTTLED = 'SWITCH_TO_THROTTLED', 'Switch to throttled'
    SWITCH_TO_BLOCKED = 'SWITCH_TO_BLOCKED', 'Switch to blocked'
    REQUIRE_MANUAL_MODE_REVIEW = 'REQUIRE_MANUAL_MODE_REVIEW', 'Require manual mode review'


class GlobalOperatingModeDecisionStatus(models.TextChoices):
    PROPOSED = 'PROPOSED', 'Proposed'
    APPLIED = 'APPLIED', 'Applied'
    SKIPPED = 'SKIPPED', 'Skipped'
    BLOCKED = 'BLOCKED', 'Blocked'


class GlobalOperatingModeSwitchStatus(models.TextChoices):
    APPLIED = 'APPLIED', 'Applied'
    SKIPPED = 'SKIPPED', 'Skipped'
    BLOCKED = 'BLOCKED', 'Blocked'
    FAILED = 'FAILED', 'Failed'


class GlobalOperatingModeRecommendationType(models.TextChoices):
    KEEP_BALANCED_MODE = 'KEEP_BALANCED_MODE', 'Keep balanced mode'
    SHIFT_TO_CAUTION_MODE = 'SHIFT_TO_CAUTION_MODE', 'Shift to caution mode'
    SHIFT_TO_MONITOR_ONLY_MODE = 'SHIFT_TO_MONITOR_ONLY_MODE', 'Shift to monitor only mode'
    ENTER_RECOVERY_MODE = 'ENTER_RECOVERY_MODE', 'Enter recovery mode'
    THROTTLE_GLOBAL_ACTIVITY = 'THROTTLE_GLOBAL_ACTIVITY', 'Throttle global activity'
    BLOCK_NEW_ACTIVITY_GLOBALLY = 'BLOCK_NEW_ACTIVITY_GLOBALLY', 'Block new activity globally'
    REQUIRE_MANUAL_MODE_REVIEW = 'REQUIRE_MANUAL_MODE_REVIEW', 'Require manual mode review'


class GlobalRuntimePostureRun(TimeStampedModel):
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    considered_signal_count = models.PositiveIntegerField(default=0)
    mode_kept_count = models.PositiveIntegerField(default=0)
    mode_switch_count = models.PositiveIntegerField(default=0)
    caution_count = models.PositiveIntegerField(default=0)
    monitor_only_count = models.PositiveIntegerField(default=0)
    recovery_mode_count = models.PositiveIntegerField(default=0)
    throttled_count = models.PositiveIntegerField(default=0)
    blocked_count = models.PositiveIntegerField(default=0)
    recommendation_summary = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']


class GlobalRuntimePostureSnapshot(TimeStampedModel):
    linked_posture_run = models.ForeignKey(
        GlobalRuntimePostureRun,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='posture_snapshots',
    )
    exposure_pressure_state = models.CharField(max_length=24, choices=ExposurePressureState.choices, default=ExposurePressureState.NORMAL)
    admission_pressure_state = models.CharField(max_length=24, choices=AdmissionPressureState.choices, default=AdmissionPressureState.NORMAL)
    session_health_state = models.CharField(max_length=12, choices=SessionHealthState.choices, default=SessionHealthState.HEALTHY)
    recent_loss_state = models.CharField(max_length=16, choices=RecentLossState.choices, default=RecentLossState.NONE)
    signal_quality_state = models.CharField(max_length=12, choices=SignalQualityState.choices, default=SignalQualityState.NORMAL)
    runtime_posture = models.CharField(max_length=12, choices=RuntimePostureState.choices, default=RuntimePostureState.NORMAL)
    safety_posture = models.CharField(max_length=12, choices=SafetyPostureState.choices, default=SafetyPostureState.NORMAL)
    incident_pressure_state = models.CharField(max_length=12, choices=IncidentPressureState.choices, default=IncidentPressureState.NONE)
    portfolio_pressure_state = models.CharField(max_length=24, choices=PortfolioPressureState.choices, default=PortfolioPressureState.NORMAL)
    snapshot_summary = models.CharField(max_length=255, blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at_snapshot = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at_snapshot', '-id']


class GlobalOperatingModeDecision(TimeStampedModel):
    linked_posture_snapshot = models.ForeignKey(GlobalRuntimePostureSnapshot, on_delete=models.CASCADE, related_name='mode_decisions')
    current_mode = models.CharField(max_length=24, choices=GlobalOperatingMode.choices, null=True, blank=True)
    target_mode = models.CharField(max_length=24, choices=GlobalOperatingMode.choices)
    decision_type = models.CharField(max_length=40, choices=GlobalOperatingModeDecisionType.choices)
    decision_status = models.CharField(max_length=12, choices=GlobalOperatingModeDecisionStatus.choices, default=GlobalOperatingModeDecisionStatus.PROPOSED)
    auto_applicable = models.BooleanField(default=False)
    decision_summary = models.CharField(max_length=255, blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at_decision = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at_decision', '-id']


class GlobalOperatingModeSwitchRecord(TimeStampedModel):
    linked_mode_decision = models.ForeignKey(GlobalOperatingModeDecision, on_delete=models.CASCADE, related_name='switch_records')
    previous_mode = models.CharField(max_length=24, choices=GlobalOperatingMode.choices, null=True, blank=True)
    applied_mode = models.CharField(max_length=24, choices=GlobalOperatingMode.choices)
    switch_status = models.CharField(max_length=12, choices=GlobalOperatingModeSwitchStatus.choices)
    switch_summary = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at_switch = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at_switch', '-id']


class GlobalOperatingModeRecommendation(TimeStampedModel):
    recommendation_type = models.CharField(max_length=40, choices=GlobalOperatingModeRecommendationType.choices)
    target_posture_snapshot = models.ForeignKey(
        GlobalRuntimePostureSnapshot,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='recommendations',
    )
    target_mode_decision = models.ForeignKey(
        GlobalOperatingModeDecision,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='recommendations',
    )
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.FloatField(default=0.5)
    blockers = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class GlobalModeEnforcementEffectType(models.TextChoices):
    NO_CHANGE = 'NO_CHANGE', 'No change'
    SOFT_REDUCTION = 'SOFT_REDUCTION', 'Soft reduction'
    THROTTLE = 'THROTTLE', 'Throttle'
    MONITOR_ONLY = 'MONITOR_ONLY', 'Monitor only'
    BLOCK_NEW_ACTIVITY = 'BLOCK_NEW_ACTIVITY', 'Block new activity'
    MANUAL_REVIEW_BIAS = 'MANUAL_REVIEW_BIAS', 'Manual review bias'


class GlobalModeImpactStatus(models.TextChoices):
    UNCHANGED = 'UNCHANGED', 'Unchanged'
    REDUCED = 'REDUCED', 'Reduced'
    THROTTLED = 'THROTTLED', 'Throttled'
    MONITOR_ONLY = 'MONITOR_ONLY', 'Monitor only'
    BLOCKED = 'BLOCKED', 'Blocked'


class GlobalModeEnforcementDecisionType(models.TextChoices):
    KEEP_DEFAULT_BEHAVIOR = 'KEEP_DEFAULT_BEHAVIOR', 'Keep default behavior'
    REDUCE_CADENCE = 'REDUCE_CADENCE', 'Reduce cadence'
    REDUCE_ADMISSION_CAPACITY = 'REDUCE_ADMISSION_CAPACITY', 'Reduce admission capacity'
    THROTTLE_EXPOSURE = 'THROTTLE_EXPOSURE', 'Throttle exposure'
    BLOCK_NEW_EXECUTION = 'BLOCK_NEW_EXECUTION', 'Block new execution'
    FORCE_MONITOR_ONLY = 'FORCE_MONITOR_ONLY', 'Force monitor only'
    REQUIRE_MANUAL_REVIEW_BIAS = 'REQUIRE_MANUAL_REVIEW_BIAS', 'Require manual review bias'


class GlobalModeEnforcementDecisionStatus(models.TextChoices):
    PROPOSED = 'PROPOSED', 'Proposed'
    APPLIED = 'APPLIED', 'Applied'
    SKIPPED = 'SKIPPED', 'Skipped'
    BLOCKED = 'BLOCKED', 'Blocked'


class GlobalModeEnforcementRecommendationType(models.TextChoices):
    KEEP_BALANCED_ENFORCEMENT = 'KEEP_BALANCED_ENFORCEMENT', 'Keep balanced enforcement'
    REDUCE_RUNTIME_INTENSITY = 'REDUCE_RUNTIME_INTENSITY', 'Reduce runtime intensity'
    ENTER_MONITOR_ONLY_BEHAVIOR = 'ENTER_MONITOR_ONLY_BEHAVIOR', 'Enter monitor only behavior'
    THROTTLE_GLOBAL_NEW_ACTIVITY = 'THROTTLE_GLOBAL_NEW_ACTIVITY', 'Throttle global new activity'
    BLOCK_NEW_EXECUTION_PATHS = 'BLOCK_NEW_EXECUTION_PATHS', 'Block new execution paths'
    BIAS_TOWARD_MANUAL_REVIEW = 'BIAS_TOWARD_MANUAL_REVIEW', 'Bias toward manual review'
    REQUIRE_MANUAL_MODE_ENFORCEMENT_REVIEW = 'REQUIRE_MANUAL_MODE_ENFORCEMENT_REVIEW', 'Require manual mode enforcement review'


class RuntimeFeedbackDiagnosticType(models.TextChoices):
    HEALTHY_RUNTIME = 'HEALTHY_RUNTIME', 'Healthy runtime'
    OVERTRADING_PRESSURE = 'OVERTRADING_PRESSURE', 'Overtrading pressure'
    QUIET_RUNTIME = 'QUIET_RUNTIME', 'Quiet runtime'
    LOSS_RECOVERY_PRESSURE = 'LOSS_RECOVERY_PRESSURE', 'Loss recovery pressure'
    BLOCKED_RUNTIME_SATURATION = 'BLOCKED_RUNTIME_SATURATION', 'Blocked runtime saturation'
    LOW_QUALITY_OPPORTUNITY_FLOW = 'LOW_QUALITY_OPPORTUNITY_FLOW', 'Low quality opportunity flow'


class RuntimeFeedbackDiagnosticSeverity(models.TextChoices):
    INFO = 'INFO', 'Info'
    CAUTION = 'CAUTION', 'Caution'
    HIGH = 'HIGH', 'High'
    CRITICAL = 'CRITICAL', 'Critical'


class RuntimeFeedbackDecisionType(models.TextChoices):
    KEEP_CURRENT_GLOBAL_MODE = 'KEEP_CURRENT_GLOBAL_MODE', 'Keep current global mode'
    SHIFT_TO_MORE_CONSERVATIVE_MODE = 'SHIFT_TO_MORE_CONSERVATIVE_MODE', 'Shift to more conservative mode'
    SHIFT_TO_MONITOR_ONLY = 'SHIFT_TO_MONITOR_ONLY', 'Shift to monitor only'
    ENTER_RECOVERY_MODE = 'ENTER_RECOVERY_MODE', 'Enter recovery mode'
    RELAX_TO_CAUTION = 'RELAX_TO_CAUTION', 'Relax to caution'
    REDUCE_ADMISSION_AND_CADENCE = 'REDUCE_ADMISSION_AND_CADENCE', 'Reduce admission and cadence'
    REQUIRE_MANUAL_RUNTIME_REVIEW = 'REQUIRE_MANUAL_RUNTIME_REVIEW', 'Require manual runtime review'


class RuntimeFeedbackDecisionStatus(models.TextChoices):
    PROPOSED = 'PROPOSED', 'Proposed'
    APPLIED = 'APPLIED', 'Applied'
    SKIPPED = 'SKIPPED', 'Skipped'
    BLOCKED = 'BLOCKED', 'Blocked'


class RuntimeFeedbackRecommendationType(models.TextChoices):
    KEEP_RUNTIME_STABLE = 'KEEP_RUNTIME_STABLE', 'Keep runtime stable'
    SHIFT_TO_CONSERVATIVE_BEHAVIOR = 'SHIFT_TO_CONSERVATIVE_BEHAVIOR', 'Shift to conservative behavior'
    ENTER_MONITOR_ONLY_TEMPORARILY = 'ENTER_MONITOR_ONLY_TEMPORARILY', 'Enter monitor only temporarily'
    ENTER_RECOVERY_MODE_FOR_LOSS_PRESSURE = 'ENTER_RECOVERY_MODE_FOR_LOSS_PRESSURE', 'Enter recovery mode for loss pressure'
    REDUCE_ADMISSION_AND_CADENCE_NOW = 'REDUCE_ADMISSION_AND_CADENCE_NOW', 'Reduce admission and cadence now'
    REQUIRE_MANUAL_RUNTIME_REVIEW = 'REQUIRE_MANUAL_RUNTIME_REVIEW', 'Require manual runtime review'


class RuntimePressureState(models.TextChoices):
    NORMAL = 'NORMAL', 'Normal'
    CAUTION = 'CAUTION', 'Caution'
    HIGH = 'HIGH', 'High'
    CRITICAL = 'CRITICAL', 'Critical'


class RuntimeFeedbackRun(TimeStampedModel):
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    considered_metric_count = models.PositiveIntegerField(default=0)
    healthy_runtime_count = models.PositiveIntegerField(default=0)
    overtrading_alert_count = models.PositiveIntegerField(default=0)
    quiet_runtime_alert_count = models.PositiveIntegerField(default=0)
    loss_pressure_alert_count = models.PositiveIntegerField(default=0)
    blocked_runtime_alert_count = models.PositiveIntegerField(default=0)
    feedback_decision_count = models.PositiveIntegerField(default=0)
    recommendation_summary = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']


class RuntimePerformanceSnapshot(TimeStampedModel):
    linked_feedback_run = models.ForeignKey(
        RuntimeFeedbackRun,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='performance_snapshots',
    )
    current_global_mode = models.CharField(max_length=24, choices=GlobalOperatingMode.choices, default=GlobalOperatingMode.BALANCED)
    recent_dispatch_count = models.PositiveIntegerField(default=0)
    recent_closed_outcome_count = models.PositiveIntegerField(default=0)
    recent_loss_count = models.PositiveIntegerField(default=0)
    recent_no_action_tick_count = models.PositiveIntegerField(default=0)
    recent_blocked_tick_count = models.PositiveIntegerField(default=0)
    recent_deferred_dispatch_count = models.PositiveIntegerField(default=0)
    recent_parked_session_count = models.PositiveIntegerField(default=0)
    recent_exposure_throttle_count = models.PositiveIntegerField(default=0)
    recent_recovery_resume_count = models.PositiveIntegerField(default=0)
    signal_quality_state = models.CharField(max_length=12, choices=SignalQualityState.choices, default=SignalQualityState.NORMAL)
    runtime_pressure_state = models.CharField(max_length=12, choices=RuntimePressureState.choices, default=RuntimePressureState.NORMAL)
    snapshot_summary = models.CharField(max_length=255, blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at', '-id']


class RuntimeDiagnosticReview(TimeStampedModel):
    linked_performance_snapshot = models.ForeignKey(
        RuntimePerformanceSnapshot,
        on_delete=models.CASCADE,
        related_name='diagnostic_reviews',
    )
    diagnostic_type = models.CharField(max_length=40, choices=RuntimeFeedbackDiagnosticType.choices)
    diagnostic_severity = models.CharField(max_length=12, choices=RuntimeFeedbackDiagnosticSeverity.choices, default=RuntimeFeedbackDiagnosticSeverity.INFO)
    diagnostic_summary = models.CharField(max_length=255, blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at', '-id']


class RuntimeFeedbackDecision(TimeStampedModel):
    linked_performance_snapshot = models.ForeignKey(
        RuntimePerformanceSnapshot,
        on_delete=models.CASCADE,
        related_name='feedback_decisions',
    )
    linked_diagnostic_review = models.ForeignKey(
        RuntimeDiagnosticReview,
        on_delete=models.CASCADE,
        related_name='feedback_decisions',
    )
    decision_type = models.CharField(max_length=48, choices=RuntimeFeedbackDecisionType.choices)
    decision_status = models.CharField(max_length=12, choices=RuntimeFeedbackDecisionStatus.choices, default=RuntimeFeedbackDecisionStatus.PROPOSED)
    auto_applicable = models.BooleanField(default=False)
    decision_summary = models.CharField(max_length=255, blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at', '-id']


class RuntimeFeedbackRecommendation(TimeStampedModel):
    recommendation_type = models.CharField(max_length=56, choices=RuntimeFeedbackRecommendationType.choices)
    target_feedback_run = models.ForeignKey(
        RuntimeFeedbackRun,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='recommendations',
    )
    target_diagnostic_review = models.ForeignKey(
        RuntimeDiagnosticReview,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='recommendations',
    )
    target_feedback_decision = models.ForeignKey(
        RuntimeFeedbackDecision,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='recommendations',
    )
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.FloatField(default=0.5)
    blockers = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at', '-id']


class RuntimeFeedbackApplyType(models.TextChoices):
    APPLY_KEEP_CURRENT_MODE = 'APPLY_KEEP_CURRENT_MODE', 'Apply keep current mode'
    APPLY_SHIFT_TO_CAUTION = 'APPLY_SHIFT_TO_CAUTION', 'Apply shift to caution'
    APPLY_SHIFT_TO_MONITOR_ONLY = 'APPLY_SHIFT_TO_MONITOR_ONLY', 'Apply shift to monitor only'
    APPLY_ENTER_RECOVERY_MODE = 'APPLY_ENTER_RECOVERY_MODE', 'Apply enter recovery mode'
    APPLY_RELAX_TO_CAUTION = 'APPLY_RELAX_TO_CAUTION', 'Apply relax to caution'
    APPLY_MANUAL_REVIEW_ONLY = 'APPLY_MANUAL_REVIEW_ONLY', 'Apply manual review only'


class RuntimeFeedbackApplyStatus(models.TextChoices):
    PROPOSED = 'PROPOSED', 'Proposed'
    APPLIED = 'APPLIED', 'Applied'
    SKIPPED = 'SKIPPED', 'Skipped'
    BLOCKED = 'BLOCKED', 'Blocked'


class RuntimeFeedbackApplyRecordStatus(models.TextChoices):
    APPLIED = 'APPLIED', 'Applied'
    SKIPPED = 'SKIPPED', 'Skipped'
    BLOCKED = 'BLOCKED', 'Blocked'
    FAILED = 'FAILED', 'Failed'


class RuntimeFeedbackApplyRecommendationType(models.TextChoices):
    APPLY_FEEDBACK_NOW = 'APPLY_FEEDBACK_NOW', 'Apply feedback now'
    KEEP_AS_ADVISORY_ONLY = 'KEEP_AS_ADVISORY_ONLY', 'Keep as advisory only'
    REFRESH_ENFORCEMENT_AFTER_MODE_SWITCH = 'REFRESH_ENFORCEMENT_AFTER_MODE_SWITCH', 'Refresh enforcement after mode switch'
    BLOCK_AUTOMATIC_FEEDBACK_APPLY = 'BLOCK_AUTOMATIC_FEEDBACK_APPLY', 'Block automatic feedback apply'
    REQUIRE_MANUAL_FEEDBACK_APPLY_REVIEW = 'REQUIRE_MANUAL_FEEDBACK_APPLY_REVIEW', 'Require manual feedback apply review'


class RuntimeFeedbackApplyRun(TimeStampedModel):
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    considered_feedback_decision_count = models.PositiveIntegerField(default=0)
    applied_count = models.PositiveIntegerField(default=0)
    manual_review_count = models.PositiveIntegerField(default=0)
    blocked_count = models.PositiveIntegerField(default=0)
    mode_switch_count = models.PositiveIntegerField(default=0)
    enforcement_refresh_count = models.PositiveIntegerField(default=0)
    recommendation_summary = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']


class RuntimeFeedbackApplyDecision(TimeStampedModel):
    linked_feedback_decision = models.ForeignKey(
        RuntimeFeedbackDecision,
        on_delete=models.CASCADE,
        related_name='apply_decisions',
    )
    linked_apply_run = models.ForeignKey(
        RuntimeFeedbackApplyRun,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='apply_decisions',
    )
    current_mode = models.CharField(max_length=24, choices=GlobalOperatingMode.choices, null=True, blank=True)
    target_mode = models.CharField(max_length=24, choices=GlobalOperatingMode.choices, null=True, blank=True)
    apply_type = models.CharField(max_length=40, choices=RuntimeFeedbackApplyType.choices)
    apply_status = models.CharField(max_length=12, choices=RuntimeFeedbackApplyStatus.choices, default=RuntimeFeedbackApplyStatus.PROPOSED)
    auto_applicable = models.BooleanField(default=False)
    apply_summary = models.CharField(max_length=255, blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at', '-id']


class RuntimeFeedbackApplyRecord(TimeStampedModel):
    linked_apply_decision = models.ForeignKey(
        RuntimeFeedbackApplyDecision,
        on_delete=models.CASCADE,
        related_name='apply_records',
    )
    record_status = models.CharField(max_length=12, choices=RuntimeFeedbackApplyRecordStatus.choices)
    previous_mode = models.CharField(max_length=24, choices=GlobalOperatingMode.choices, null=True, blank=True)
    applied_mode = models.CharField(max_length=24, choices=GlobalOperatingMode.choices, null=True, blank=True)
    enforcement_refreshed = models.BooleanField(default=False)
    record_summary = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at', '-id']


class RuntimeFeedbackApplyRecommendation(TimeStampedModel):
    recommendation_type = models.CharField(max_length=56, choices=RuntimeFeedbackApplyRecommendationType.choices)
    target_feedback_decision = models.ForeignKey(
        RuntimeFeedbackDecision,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='apply_recommendations',
    )
    target_apply_decision = models.ForeignKey(
        RuntimeFeedbackApplyDecision,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='recommendations',
    )
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.FloatField(default=0.5)
    blockers = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at', '-id']


class RuntimeModeFeedbackPressureState(models.TextChoices):
    LOW = 'LOW', 'Low'
    NORMAL = 'NORMAL', 'Normal'
    HIGH = 'HIGH', 'High'
    CRITICAL = 'CRITICAL', 'Critical'


class RuntimeModeTransitionRiskState(models.TextChoices):
    LOW = 'LOW', 'Low'
    CAUTION = 'CAUTION', 'Caution'
    HIGH = 'HIGH', 'High'
    CRITICAL = 'CRITICAL', 'Critical'


class RuntimeModeStabilityReviewType(models.TextChoices):
    STABLE_TRANSITION = 'STABLE_TRANSITION', 'Stable transition'
    EARLY_RELAX_ATTEMPT = 'EARLY_RELAX_ATTEMPT', 'Early relax attempt'
    FLAPPING_RISK = 'FLAPPING_RISK', 'Flapping risk'
    INSUFFICIENT_DWELL_TIME = 'INSUFFICIENT_DWELL_TIME', 'Insufficient dwell time'
    SAFE_RECOVERY_ENTRY = 'SAFE_RECOVERY_ENTRY', 'Safe recovery entry'
    SAFE_RELAXATION_WINDOW = 'SAFE_RELAXATION_WINDOW', 'Safe relaxation window'


class RuntimeModeStabilityReviewSeverity(models.TextChoices):
    INFO = 'INFO', 'Info'
    CAUTION = 'CAUTION', 'Caution'
    HIGH = 'HIGH', 'High'
    CRITICAL = 'CRITICAL', 'Critical'


class RuntimeModeTransitionDecisionType(models.TextChoices):
    ALLOW_MODE_SWITCH = 'ALLOW_MODE_SWITCH', 'Allow mode switch'
    DEFER_MODE_SWITCH = 'DEFER_MODE_SWITCH', 'Defer mode switch'
    KEEP_CURRENT_MODE_FOR_DWELL = 'KEEP_CURRENT_MODE_FOR_DWELL', 'Keep current mode for dwell'
    REQUIRE_MANUAL_STABILITY_REVIEW = 'REQUIRE_MANUAL_STABILITY_REVIEW', 'Require manual stability review'
    BLOCK_MODE_SWITCH = 'BLOCK_MODE_SWITCH', 'Block mode switch'


class RuntimeModeTransitionDecisionStatus(models.TextChoices):
    PROPOSED = 'PROPOSED', 'Proposed'
    SKIPPED = 'SKIPPED', 'Skipped'
    BLOCKED = 'BLOCKED', 'Blocked'


class RuntimeModeStabilizationRecommendationType(models.TextChoices):
    ALLOW_TRANSITION_NOW = 'ALLOW_TRANSITION_NOW', 'Allow transition now'
    HOLD_CURRENT_MODE_LONGER = 'HOLD_CURRENT_MODE_LONGER', 'Hold current mode longer'
    DEFER_RELAXATION = 'DEFER_RELAXATION', 'Defer relaxation'
    BLOCK_FLAPPING_TRANSITION = 'BLOCK_FLAPPING_TRANSITION', 'Block flapping transition'
    REQUIRE_MANUAL_STABILITY_REVIEW = 'REQUIRE_MANUAL_STABILITY_REVIEW', 'Require manual stability review'
    KEEP_RECOVERY_MODE_UNTIL_STABLE = 'KEEP_RECOVERY_MODE_UNTIL_STABLE', 'Keep recovery mode until stable'


class RuntimeModeStabilizationRun(TimeStampedModel):
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    considered_transition_count = models.PositiveIntegerField(default=0)
    allowed_count = models.PositiveIntegerField(default=0)
    deferred_count = models.PositiveIntegerField(default=0)
    dwell_hold_count = models.PositiveIntegerField(default=0)
    blocked_count = models.PositiveIntegerField(default=0)
    manual_review_count = models.PositiveIntegerField(default=0)
    recommendation_summary = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']


class RuntimeModeTransitionSnapshot(TimeStampedModel):
    linked_run = models.ForeignKey(
        RuntimeModeStabilizationRun,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='transition_snapshots',
    )
    linked_feedback_decision = models.ForeignKey(
        RuntimeFeedbackDecision,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='mode_transition_snapshots',
    )
    current_mode = models.CharField(max_length=24, choices=GlobalOperatingMode.choices)
    target_mode = models.CharField(max_length=24, choices=GlobalOperatingMode.choices)
    current_mode_started_at = models.DateTimeField(null=True, blank=True)
    time_in_current_mode_seconds = models.PositiveIntegerField(default=0)
    recent_switch_count = models.PositiveIntegerField(default=0)
    recent_switch_window_seconds = models.PositiveIntegerField(default=0)
    last_switch_at = models.DateTimeField(null=True, blank=True)
    feedback_pressure_state = models.CharField(
        max_length=12,
        choices=RuntimeModeFeedbackPressureState.choices,
        default=RuntimeModeFeedbackPressureState.NORMAL,
    )
    transition_risk_state = models.CharField(
        max_length=12,
        choices=RuntimeModeTransitionRiskState.choices,
        default=RuntimeModeTransitionRiskState.LOW,
    )
    snapshot_summary = models.CharField(max_length=255, blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class RuntimeModeStabilityReview(TimeStampedModel):
    linked_transition_snapshot = models.ForeignKey(
        RuntimeModeTransitionSnapshot,
        on_delete=models.CASCADE,
        related_name='stability_reviews',
    )
    review_type = models.CharField(max_length=40, choices=RuntimeModeStabilityReviewType.choices)
    review_severity = models.CharField(
        max_length=12,
        choices=RuntimeModeStabilityReviewSeverity.choices,
        default=RuntimeModeStabilityReviewSeverity.INFO,
    )
    review_summary = models.CharField(max_length=255, blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class RuntimeModeTransitionDecision(TimeStampedModel):
    linked_transition_snapshot = models.ForeignKey(
        RuntimeModeTransitionSnapshot,
        on_delete=models.CASCADE,
        related_name='transition_decisions',
    )
    linked_stability_review = models.ForeignKey(
        RuntimeModeStabilityReview,
        on_delete=models.CASCADE,
        related_name='transition_decisions',
    )
    decision_type = models.CharField(max_length=40, choices=RuntimeModeTransitionDecisionType.choices)
    decision_status = models.CharField(
        max_length=12,
        choices=RuntimeModeTransitionDecisionStatus.choices,
        default=RuntimeModeTransitionDecisionStatus.PROPOSED,
    )
    auto_applicable = models.BooleanField(default=False)
    decision_summary = models.CharField(max_length=255, blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class RuntimeModeStabilizationRecommendation(TimeStampedModel):
    target_transition_snapshot = models.ForeignKey(
        RuntimeModeTransitionSnapshot,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='recommendations',
    )
    target_stability_review = models.ForeignKey(
        RuntimeModeStabilityReview,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='recommendations',
    )
    target_transition_decision = models.ForeignKey(
        RuntimeModeTransitionDecision,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='recommendations',
    )
    recommendation_type = models.CharField(max_length=48, choices=RuntimeModeStabilizationRecommendationType.choices)
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.FloatField(default=0.5)
    blockers = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class GlobalModeEnforcementRun(TimeStampedModel):
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    current_mode = models.CharField(max_length=24, choices=GlobalOperatingMode.choices, default=GlobalOperatingMode.BALANCED)
    considered_module_count = models.PositiveIntegerField(default=0)
    affected_module_count = models.PositiveIntegerField(default=0)
    restricted_module_count = models.PositiveIntegerField(default=0)
    throttled_module_count = models.PositiveIntegerField(default=0)
    blocked_module_count = models.PositiveIntegerField(default=0)
    monitor_only_module_count = models.PositiveIntegerField(default=0)
    recommendation_summary = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']


class GlobalModeModuleImpact(TimeStampedModel):
    linked_enforcement_run = models.ForeignKey(GlobalModeEnforcementRun, on_delete=models.CASCADE, related_name='module_impacts')
    current_mode = models.CharField(max_length=24, choices=GlobalOperatingMode.choices)
    module_name = models.CharField(max_length=64)
    impact_status = models.CharField(max_length=24, choices=GlobalModeImpactStatus.choices, default=GlobalModeImpactStatus.UNCHANGED)
    effective_behavior_summary = models.CharField(max_length=255, blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at', '-id']


class GlobalModeEnforcementDecision(TimeStampedModel):
    linked_enforcement_run = models.ForeignKey(GlobalModeEnforcementRun, on_delete=models.CASCADE, related_name='enforcement_decisions')
    module_name = models.CharField(max_length=64)
    decision_type = models.CharField(max_length=48, choices=GlobalModeEnforcementDecisionType.choices)
    decision_status = models.CharField(max_length=12, choices=GlobalModeEnforcementDecisionStatus.choices, default=GlobalModeEnforcementDecisionStatus.PROPOSED)
    auto_applicable = models.BooleanField(default=True)
    decision_summary = models.CharField(max_length=255, blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at', '-id']


class GlobalModeEnforcementRecommendation(TimeStampedModel):
    recommendation_type = models.CharField(max_length=56, choices=GlobalModeEnforcementRecommendationType.choices)
    target_enforcement_run = models.ForeignKey(
        GlobalModeEnforcementRun,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='recommendations',
    )
    target_module_impact = models.ForeignKey(
        GlobalModeModuleImpact,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='recommendations',
    )
    target_enforcement_decision = models.ForeignKey(
        GlobalModeEnforcementDecision,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='recommendations',
    )
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.FloatField(default=0.5)
    blockers = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at', '-id']

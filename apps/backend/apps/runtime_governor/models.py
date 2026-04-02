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

from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel


class MissionControlSessionStatus(models.TextChoices):
    IDLE = 'IDLE', 'Idle'
    RUNNING = 'RUNNING', 'Running'
    PAUSED = 'PAUSED', 'Paused'
    DEGRADED = 'DEGRADED', 'Degraded'
    STOPPED = 'STOPPED', 'Stopped'
    FAILED = 'FAILED', 'Failed'


class MissionControlCycleStatus(models.TextChoices):
    SUCCESS = 'SUCCESS', 'Success'
    PARTIAL = 'PARTIAL', 'Partial'
    FAILED = 'FAILED', 'Failed'
    SKIPPED = 'SKIPPED', 'Skipped'


class MissionControlStepStatus(models.TextChoices):
    SUCCESS = 'SUCCESS', 'Success'
    PARTIAL = 'PARTIAL', 'Partial'
    FAILED = 'FAILED', 'Failed'
    SKIPPED = 'SKIPPED', 'Skipped'


class AutonomousMissionRuntimeStatus(models.TextChoices):
    RUNNING = 'RUNNING', 'Running'
    PAUSED = 'PAUSED', 'Paused'
    STOPPED = 'STOPPED', 'Stopped'
    DEGRADED = 'DEGRADED', 'Degraded'
    BLOCKED = 'BLOCKED', 'Blocked'
    COMPLETED = 'COMPLETED', 'Completed'


class AutonomousMissionCyclePlanStatus(models.TextChoices):
    READY = 'READY', 'Ready'
    REDUCED = 'REDUCED', 'Reduced'
    BLOCKED = 'BLOCKED', 'Blocked'
    SKIPPED = 'SKIPPED', 'Skipped'


class AutonomousMissionCycleExecutionStatus(models.TextChoices):
    STARTED = 'STARTED', 'Started'
    COMPLETED = 'COMPLETED', 'Completed'
    PARTIAL = 'PARTIAL', 'Partial'
    BLOCKED = 'BLOCKED', 'Blocked'
    FAILED = 'FAILED', 'Failed'
    SKIPPED = 'SKIPPED', 'Skipped'


class AutonomousMissionCycleOutcomeStatus(models.TextChoices):
    NO_ACTION = 'NO_ACTION', 'No action'
    WATCH_ONLY = 'WATCH_ONLY', 'Watch only'
    EXECUTION_OCCURRED = 'EXECUTION_OCCURRED', 'Execution occurred'
    EXECUTION_REDUCED = 'EXECUTION_REDUCED', 'Execution reduced'
    POSITIONS_UPDATED = 'POSITIONS_UPDATED', 'Positions updated'
    OUTCOMES_CLOSED = 'OUTCOMES_CLOSED', 'Outcomes closed'
    LEARNING_UPDATED = 'LEARNING_UPDATED', 'Learning updated'
    BLOCKED = 'BLOCKED', 'Blocked'


class AutonomousMissionRecommendationType(models.TextChoices):
    RUN_FULL_CYCLE = 'RUN_FULL_CYCLE', 'Run full cycle'
    RUN_REDUCED_CYCLE = 'RUN_REDUCED_CYCLE', 'Run reduced cycle'
    SKIP_EXECUTION_AND_MONITOR_ONLY = 'SKIP_EXECUTION_AND_MONITOR_ONLY', 'Skip execution and monitor only'
    PAUSE_FOR_PORTFOLIO_PRESSURE = 'PAUSE_FOR_PORTFOLIO_PRESSURE', 'Pause for portfolio pressure'
    PAUSE_FOR_SAFETY_OR_RUNTIME_BLOCK = 'PAUSE_FOR_SAFETY_OR_RUNTIME_BLOCK', 'Pause for safety or runtime block'
    REQUIRE_MANUAL_RUNTIME_REVIEW = 'REQUIRE_MANUAL_RUNTIME_REVIEW', 'Require manual runtime review'


class MissionControlState(TimeStampedModel):
    status = models.CharField(max_length=12, choices=MissionControlSessionStatus.choices, default=MissionControlSessionStatus.IDLE)
    active_session = models.ForeignKey('MissionControlSession', null=True, blank=True, on_delete=models.SET_NULL, related_name='state_records')
    pause_requested = models.BooleanField(default=False)
    stop_requested = models.BooleanField(default=False)
    cycle_in_progress = models.BooleanField(default=False)
    last_heartbeat_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    profile_slug = models.CharField(max_length=40, default='balanced_mission_control')
    settings_snapshot = models.JSONField(default=dict, blank=True)


class MissionControlSession(TimeStampedModel):
    status = models.CharField(max_length=12, choices=MissionControlSessionStatus.choices, default=MissionControlSessionStatus.IDLE)
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)
    cycle_count = models.PositiveIntegerField(default=0)
    last_cycle_at = models.DateTimeField(null=True, blank=True)
    summary = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']


class MissionControlCycle(TimeStampedModel):
    session = models.ForeignKey(MissionControlSession, on_delete=models.CASCADE, related_name='cycles')
    cycle_number = models.PositiveIntegerField()
    status = models.CharField(max_length=12, choices=MissionControlCycleStatus.choices, default=MissionControlCycleStatus.SUCCESS)
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)
    steps_run_count = models.PositiveIntegerField(default=0)
    opportunities_built = models.PositiveIntegerField(default=0)
    proposals_generated = models.PositiveIntegerField(default=0)
    queue_count = models.PositiveIntegerField(default=0)
    auto_execute_count = models.PositiveIntegerField(default=0)
    blocked_count = models.PositiveIntegerField(default=0)
    summary = models.CharField(max_length=255, blank=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']
        constraints = [
            models.UniqueConstraint(fields=['session', 'cycle_number'], name='mission_control_session_cycle_unique'),
        ]


class MissionControlStep(TimeStampedModel):
    cycle = models.ForeignKey(MissionControlCycle, on_delete=models.CASCADE, related_name='steps')
    step_type = models.CharField(max_length=48)
    status = models.CharField(max_length=12, choices=MissionControlStepStatus.choices, default=MissionControlStepStatus.SUCCESS)
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)
    summary = models.CharField(max_length=255, blank=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['started_at', 'id']


class AutonomousMissionRuntimeRun(TimeStampedModel):
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    runtime_status = models.CharField(max_length=12, choices=AutonomousMissionRuntimeStatus.choices, default=AutonomousMissionRuntimeStatus.RUNNING)
    cycle_count = models.PositiveIntegerField(default=0)
    executed_cycle_count = models.PositiveIntegerField(default=0)
    blocked_cycle_count = models.PositiveIntegerField(default=0)
    dispatch_count = models.PositiveIntegerField(default=0)
    closed_outcome_count = models.PositiveIntegerField(default=0)
    postmortem_handoff_count = models.PositiveIntegerField(default=0)
    learning_handoff_count = models.PositiveIntegerField(default=0)
    reuse_applied_count = models.PositiveIntegerField(default=0)
    recommendation_summary = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']


class AutonomousMissionCyclePlan(TimeStampedModel):
    linked_runtime_run = models.ForeignKey(AutonomousMissionRuntimeRun, on_delete=models.CASCADE, related_name='cycle_plans')
    planned_step_flags = models.JSONField(default=dict, blank=True)
    plan_status = models.CharField(max_length=12, choices=AutonomousMissionCyclePlanStatus.choices, default=AutonomousMissionCyclePlanStatus.READY)
    runtime_mode = models.CharField(max_length=32, blank=True)
    portfolio_posture = models.CharField(max_length=32, blank=True)
    safety_posture = models.CharField(max_length=32, blank=True)
    degraded_mode_state = models.CharField(max_length=32, blank=True)
    plan_summary = models.CharField(max_length=255, blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class AutonomousMissionCycleExecution(TimeStampedModel):
    linked_cycle_plan = models.OneToOneField(AutonomousMissionCyclePlan, on_delete=models.CASCADE, related_name='execution')
    execution_status = models.CharField(max_length=12, choices=AutonomousMissionCycleExecutionStatus.choices, default=AutonomousMissionCycleExecutionStatus.STARTED)
    executed_steps = models.JSONField(default=list, blank=True)
    skipped_steps = models.JSONField(default=list, blank=True)
    blocked_steps = models.JSONField(default=list, blank=True)
    linked_scan_run = models.CharField(max_length=64, blank=True)
    linked_pursuit_run = models.CharField(max_length=64, blank=True)
    linked_prediction_intake_run = models.CharField(max_length=64, blank=True)
    linked_risk_intake_run = models.CharField(max_length=64, blank=True)
    linked_execution_intake_run = models.CharField(max_length=64, blank=True)
    linked_position_watch_run = models.CharField(max_length=64, blank=True)
    linked_outcome_handoff_run = models.CharField(max_length=64, blank=True)
    linked_feedback_reuse_run = models.CharField(max_length=64, blank=True)
    execution_summary = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class AutonomousMissionCycleOutcome(TimeStampedModel):
    linked_cycle_execution = models.OneToOneField(AutonomousMissionCycleExecution, on_delete=models.CASCADE, related_name='outcome')
    outcome_status = models.CharField(max_length=24, choices=AutonomousMissionCycleOutcomeStatus.choices, default=AutonomousMissionCycleOutcomeStatus.NO_ACTION)
    dispatch_count = models.PositiveIntegerField(default=0)
    watch_update_count = models.PositiveIntegerField(default=0)
    close_action_count = models.PositiveIntegerField(default=0)
    postmortem_count = models.PositiveIntegerField(default=0)
    learning_count = models.PositiveIntegerField(default=0)
    reuse_count = models.PositiveIntegerField(default=0)
    outcome_summary = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class AutonomousMissionRuntimeRecommendation(TimeStampedModel):
    recommendation_type = models.CharField(max_length=48, choices=AutonomousMissionRecommendationType.choices)
    target_runtime_run = models.ForeignKey(AutonomousMissionRuntimeRun, on_delete=models.SET_NULL, null=True, blank=True, related_name='recommendations')
    target_cycle_plan = models.ForeignKey(AutonomousMissionCyclePlan, on_delete=models.SET_NULL, null=True, blank=True, related_name='recommendations')
    target_cycle_execution = models.ForeignKey(AutonomousMissionCycleExecution, on_delete=models.SET_NULL, null=True, blank=True, related_name='recommendations')
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.FloatField(default=0.5)
    blockers = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class AutonomousRuntimeSessionStatus(models.TextChoices):
    RUNNING = 'RUNNING', 'Running'
    PAUSED = 'PAUSED', 'Paused'
    STOPPED = 'STOPPED', 'Stopped'
    DEGRADED = 'DEGRADED', 'Degraded'
    BLOCKED = 'BLOCKED', 'Blocked'
    COMPLETED = 'COMPLETED', 'Completed'


class AutonomousRuntimeTickMode(models.TextChoices):
    FULL_CYCLE = 'FULL_CYCLE', 'Full cycle'
    REDUCED_CYCLE = 'REDUCED_CYCLE', 'Reduced cycle'
    MONITOR_ONLY = 'MONITOR_ONLY', 'Monitor only'
    SKIP = 'SKIP', 'Skip'


class AutonomousRuntimeTickStatus(models.TextChoices):
    PLANNED = 'PLANNED', 'Planned'
    STARTED = 'STARTED', 'Started'
    COMPLETED = 'COMPLETED', 'Completed'
    PARTIAL = 'PARTIAL', 'Partial'
    BLOCKED = 'BLOCKED', 'Blocked'
    SKIPPED = 'SKIPPED', 'Skipped'
    FAILED = 'FAILED', 'Failed'


class AutonomousCadenceMode(models.TextChoices):
    RUN_NOW = 'RUN_NOW', 'Run now'
    WAIT_SHORT = 'WAIT_SHORT', 'Wait short'
    WAIT_LONG = 'WAIT_LONG', 'Wait long'
    MONITOR_ONLY_NEXT = 'MONITOR_ONLY_NEXT', 'Monitor only next'
    PAUSE_SESSION = 'PAUSE_SESSION', 'Pause session'
    STOP_SESSION = 'STOP_SESSION', 'Stop session'


class AutonomousSignalPressureState(models.TextChoices):
    HIGH = 'HIGH', 'High'
    NORMAL = 'NORMAL', 'Normal'
    LOW = 'LOW', 'Low'
    QUIET = 'QUIET', 'Quiet'


class AutonomousCooldownType(models.TextChoices):
    POST_DISPATCH_COOLDOWN = 'POST_DISPATCH_COOLDOWN', 'Post dispatch cooldown'
    POST_LOSS_COOLDOWN = 'POST_LOSS_COOLDOWN', 'Post loss cooldown'
    PORTFOLIO_PRESSURE_COOLDOWN = 'PORTFOLIO_PRESSURE_COOLDOWN', 'Portfolio pressure cooldown'
    RUNTIME_CAUTION_COOLDOWN = 'RUNTIME_CAUTION_COOLDOWN', 'Runtime caution cooldown'
    QUIET_MARKET_COOLDOWN = 'QUIET_MARKET_COOLDOWN', 'Quiet market cooldown'


class AutonomousCooldownStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Active'
    EXPIRED = 'EXPIRED', 'Expired'
    CANCELLED = 'CANCELLED', 'Cancelled'


class AutonomousSessionRecommendationType(models.TextChoices):
    CONTINUE_RUNNING = 'CONTINUE_RUNNING', 'Continue running'
    RUN_REDUCED_NEXT_TICK = 'RUN_REDUCED_NEXT_TICK', 'Run reduced next tick'
    PAUSE_FOR_PORTFOLIO_PRESSURE = 'PAUSE_FOR_PORTFOLIO_PRESSURE', 'Pause for portfolio pressure'
    PAUSE_FOR_SAFETY_BLOCK = 'PAUSE_FOR_SAFETY_BLOCK', 'Pause for safety block'
    STOP_FOR_RUNTIME_HARD_BLOCK = 'STOP_FOR_RUNTIME_HARD_BLOCK', 'Stop for runtime hard block'
    WAIT_FOR_SIGNAL_REFRESH = 'WAIT_FOR_SIGNAL_REFRESH', 'Wait for signal refresh'
    REQUIRE_MANUAL_SESSION_REVIEW = 'REQUIRE_MANUAL_SESSION_REVIEW', 'Require manual session review'


class AutonomousTimingStatus(models.TextChoices):
    DUE_NOW = 'DUE_NOW', 'Due now'
    WAIT_SHORT = 'WAIT_SHORT', 'Wait short'
    WAIT_LONG = 'WAIT_LONG', 'Wait long'
    MONITOR_ONLY_WINDOW = 'MONITOR_ONLY_WINDOW', 'Monitor only window'
    PAUSE_RECOMMENDED = 'PAUSE_RECOMMENDED', 'Pause recommended'
    STOP_RECOMMENDED = 'STOP_RECOMMENDED', 'Stop recommended'


class AutonomousStopEvaluationType(models.TextChoices):
    PERSISTENT_BLOCKS = 'PERSISTENT_BLOCKS', 'Persistent blocks'
    REPEATED_NO_ACTION = 'REPEATED_NO_ACTION', 'Repeated no action'
    QUIET_MARKET = 'QUIET_MARKET', 'Quiet market'
    POST_LOSS_COOLDOWN = 'POST_LOSS_COOLDOWN', 'Post-loss cooldown'
    PORTFOLIO_PRESSURE_PERSISTENT = 'PORTFOLIO_PRESSURE_PERSISTENT', 'Portfolio pressure persistent'
    RUNTIME_OR_SAFETY_STOP = 'RUNTIME_OR_SAFETY_STOP', 'Runtime or safety stop'


class AutonomousStopEvaluationStatus(models.TextChoices):
    INFO = 'INFO', 'Info'
    CAUTION = 'CAUTION', 'Caution'
    ACTIONABLE = 'ACTIONABLE', 'Actionable'
    CRITICAL = 'CRITICAL', 'Critical'


class AutonomousTimingDecisionType(models.TextChoices):
    RUN_NOW = 'RUN_NOW', 'Run now'
    WAIT_SHORT = 'WAIT_SHORT', 'Wait short'
    WAIT_LONG = 'WAIT_LONG', 'Wait long'
    MONITOR_ONLY_NEXT = 'MONITOR_ONLY_NEXT', 'Monitor only next'
    PAUSE_SESSION = 'PAUSE_SESSION', 'Pause session'
    STOP_SESSION = 'STOP_SESSION', 'Stop session'


class AutonomousTimingDecisionStatus(models.TextChoices):
    PROPOSED = 'PROPOSED', 'Proposed'
    APPLIED = 'APPLIED', 'Applied'
    SKIPPED = 'SKIPPED', 'Skipped'
    BLOCKED = 'BLOCKED', 'Blocked'


class AutonomousTimingRecommendationType(models.TextChoices):
    RUN_NEXT_TICK_IMMEDIATELY = 'RUN_NEXT_TICK_IMMEDIATELY', 'Run next tick immediately'
    WAIT_FOR_SHORT_INTERVAL = 'WAIT_FOR_SHORT_INTERVAL', 'Wait for short interval'
    WAIT_FOR_LONG_INTERVAL = 'WAIT_FOR_LONG_INTERVAL', 'Wait for long interval'
    ENTER_MONITOR_ONLY_WINDOW = 'ENTER_MONITOR_ONLY_WINDOW', 'Enter monitor-only window'
    PAUSE_SESSION_FOR_QUIET_MARKET = 'PAUSE_SESSION_FOR_QUIET_MARKET', 'Pause session for quiet market'
    STOP_SESSION_FOR_PERSISTENT_BLOCKS = 'STOP_SESSION_FOR_PERSISTENT_BLOCKS', 'Stop session for persistent blocks'
    REQUIRE_MANUAL_TIMING_REVIEW = 'REQUIRE_MANUAL_TIMING_REVIEW', 'Require manual timing review'


class AutonomousProfilePortfolioPressureState(models.TextChoices):
    NORMAL = 'NORMAL', 'Normal'
    CAUTION = 'CAUTION', 'Caution'
    THROTTLED = 'THROTTLED', 'Throttled'
    BLOCK_NEW_ENTRIES = 'BLOCK_NEW_ENTRIES', 'Block new entries'


class AutonomousProfileRuntimePosture(models.TextChoices):
    NORMAL = 'NORMAL', 'Normal'
    CAUTION = 'CAUTION', 'Caution'
    BLOCKED = 'BLOCKED', 'Blocked'


class AutonomousProfileSafetyPosture(models.TextChoices):
    NORMAL = 'NORMAL', 'Normal'
    CAUTION = 'CAUTION', 'Caution'
    HARD_BLOCK = 'HARD_BLOCK', 'Hard block'


class AutonomousRecentLossState(models.TextChoices):
    NONE = 'NONE', 'None'
    RECENT_LOSS = 'RECENT_LOSS', 'Recent loss'
    REPEATED_LOSS = 'REPEATED_LOSS', 'Repeated loss'


class AutonomousProfileActivityState(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Active'
    LOW_ACTIVITY = 'LOW_ACTIVITY', 'Low activity'
    REPEATED_NO_ACTION = 'REPEATED_NO_ACTION', 'Repeated no action'
    REPEATED_BLOCKED = 'REPEATED_BLOCKED', 'Repeated blocked'


class AutonomousProfileContextStatus(models.TextChoices):
    STABLE = 'STABLE', 'Stable'
    NEEDS_MORE_CONSERVATIVE_PROFILE = 'NEEDS_MORE_CONSERVATIVE_PROFILE', 'Needs more conservative profile'
    NEEDS_MORE_ACTIVE_PROFILE = 'NEEDS_MORE_ACTIVE_PROFILE', 'Needs more active profile'
    HOLD_CURRENT = 'HOLD_CURRENT', 'Hold current'
    BLOCKED = 'BLOCKED', 'Blocked'


class AutonomousProfileSwitchDecisionType(models.TextChoices):
    KEEP_CURRENT_PROFILE = 'KEEP_CURRENT_PROFILE', 'Keep current profile'
    SWITCH_TO_CONSERVATIVE_QUIET = 'SWITCH_TO_CONSERVATIVE_QUIET', 'Switch to conservative quiet'
    SWITCH_TO_MONITOR_HEAVY = 'SWITCH_TO_MONITOR_HEAVY', 'Switch to monitor heavy'
    SWITCH_TO_BALANCED_LOCAL = 'SWITCH_TO_BALANCED_LOCAL', 'Switch to balanced local'
    REQUIRE_MANUAL_PROFILE_REVIEW = 'REQUIRE_MANUAL_PROFILE_REVIEW', 'Require manual profile review'
    BLOCK_PROFILE_SWITCH = 'BLOCK_PROFILE_SWITCH', 'Block profile switch'


class AutonomousProfileSwitchDecisionStatus(models.TextChoices):
    PROPOSED = 'PROPOSED', 'Proposed'
    APPLIED = 'APPLIED', 'Applied'
    SKIPPED = 'SKIPPED', 'Skipped'
    BLOCKED = 'BLOCKED', 'Blocked'


class AutonomousProfileSwitchStatus(models.TextChoices):
    APPLIED = 'APPLIED', 'Applied'
    SKIPPED = 'SKIPPED', 'Skipped'
    BLOCKED = 'BLOCKED', 'Blocked'


class AutonomousProfileRecommendationType(models.TextChoices):
    KEEP_BALANCED_PROFILE = 'KEEP_BALANCED_PROFILE', 'Keep balanced profile'
    SHIFT_TO_CONSERVATIVE_QUIET_PROFILE = 'SHIFT_TO_CONSERVATIVE_QUIET_PROFILE', 'Shift to conservative quiet profile'
    SHIFT_TO_MONITOR_HEAVY_PROFILE = 'SHIFT_TO_MONITOR_HEAVY_PROFILE', 'Shift to monitor heavy profile'
    RESTORE_BALANCED_PROFILE = 'RESTORE_BALANCED_PROFILE', 'Restore balanced profile'
    REQUIRE_MANUAL_PROFILE_REVIEW = 'REQUIRE_MANUAL_PROFILE_REVIEW', 'Require manual profile review'
    BLOCK_AUTOMATIC_PROFILE_SWITCH = 'BLOCK_AUTOMATIC_PROFILE_SWITCH', 'Block automatic profile switch'


class AutonomousScheduleProfile(TimeStampedModel):
    slug = models.SlugField(max_length=64, unique=True)
    display_name = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)
    base_interval_seconds = models.PositiveIntegerField(default=60)
    reduced_interval_seconds = models.PositiveIntegerField(default=30)
    monitor_only_interval_seconds = models.PositiveIntegerField(default=180)
    cooldown_extension_seconds = models.PositiveIntegerField(default=120)
    max_no_action_ticks_before_pause = models.PositiveIntegerField(default=5)
    max_quiet_ticks_before_wait_long = models.PositiveIntegerField(default=3)
    max_consecutive_blocked_ticks_before_stop = models.PositiveIntegerField(default=4)
    enable_auto_pause_for_quiet_markets = models.BooleanField(default=True)
    enable_auto_stop_for_persistent_blocks = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['slug', '-id']


class AutonomousRuntimeSession(TimeStampedModel):
    started_at = models.DateTimeField(default=timezone.now)
    stopped_at = models.DateTimeField(null=True, blank=True)
    session_status = models.CharField(max_length=12, choices=AutonomousRuntimeSessionStatus.choices, default=AutonomousRuntimeSessionStatus.RUNNING)
    runtime_mode = models.CharField(max_length=32, blank=True)
    profile_slug = models.CharField(max_length=40, blank=True)
    tick_count = models.PositiveIntegerField(default=0)
    executed_tick_count = models.PositiveIntegerField(default=0)
    skipped_tick_count = models.PositiveIntegerField(default=0)
    dispatch_count = models.PositiveIntegerField(default=0)
    closed_outcome_count = models.PositiveIntegerField(default=0)
    pause_reason_codes = models.JSONField(default=list, blank=True)
    stop_reason_codes = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    linked_schedule_profile = models.ForeignKey(
        'AutonomousScheduleProfile',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='runtime_sessions',
    )

    class Meta:
        ordering = ['-started_at', '-id']


class AutonomousRuntimeTick(TimeStampedModel):
    linked_session = models.ForeignKey(AutonomousRuntimeSession, on_delete=models.CASCADE, related_name='ticks')
    tick_index = models.PositiveIntegerField()
    planned_tick_mode = models.CharField(max_length=20, choices=AutonomousRuntimeTickMode.choices, default=AutonomousRuntimeTickMode.FULL_CYCLE)
    tick_status = models.CharField(max_length=12, choices=AutonomousRuntimeTickStatus.choices, default=AutonomousRuntimeTickStatus.PLANNED)
    linked_runtime_run = models.ForeignKey(AutonomousMissionRuntimeRun, null=True, blank=True, on_delete=models.SET_NULL, related_name='runtime_ticks')
    linked_cycle_plan = models.ForeignKey(AutonomousMissionCyclePlan, null=True, blank=True, on_delete=models.SET_NULL, related_name='runtime_ticks')
    linked_cycle_execution = models.ForeignKey(AutonomousMissionCycleExecution, null=True, blank=True, on_delete=models.SET_NULL, related_name='runtime_ticks')
    linked_cycle_outcome = models.ForeignKey(AutonomousMissionCycleOutcome, null=True, blank=True, on_delete=models.SET_NULL, related_name='runtime_ticks')
    tick_summary = models.CharField(max_length=255, blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        constraints = [
            models.UniqueConstraint(fields=['linked_session', 'tick_index'], name='autonomous_runtime_session_tick_unique'),
        ]


class AutonomousCadenceDecision(TimeStampedModel):
    linked_session = models.ForeignKey(AutonomousRuntimeSession, on_delete=models.CASCADE, related_name='cadence_decisions')
    linked_previous_tick = models.ForeignKey(AutonomousRuntimeTick, null=True, blank=True, on_delete=models.SET_NULL, related_name='next_cadence_decisions')
    cadence_mode = models.CharField(max_length=20, choices=AutonomousCadenceMode.choices, default=AutonomousCadenceMode.RUN_NOW)
    cadence_reason_codes = models.JSONField(default=list, blank=True)
    portfolio_posture = models.CharField(max_length=32, blank=True)
    runtime_posture = models.CharField(max_length=32, blank=True)
    safety_posture = models.CharField(max_length=32, blank=True)
    signal_pressure_state = models.CharField(max_length=12, choices=AutonomousSignalPressureState.choices, default=AutonomousSignalPressureState.NORMAL)
    decision_summary = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class AutonomousCooldownState(TimeStampedModel):
    linked_session = models.ForeignKey(AutonomousRuntimeSession, on_delete=models.CASCADE, related_name='cooldowns')
    cooldown_type = models.CharField(max_length=36, choices=AutonomousCooldownType.choices)
    cooldown_status = models.CharField(max_length=12, choices=AutonomousCooldownStatus.choices, default=AutonomousCooldownStatus.ACTIVE)
    started_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    cooldown_summary = models.CharField(max_length=255, blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']


class AutonomousSessionRecommendation(TimeStampedModel):
    recommendation_type = models.CharField(max_length=40, choices=AutonomousSessionRecommendationType.choices)
    target_session = models.ForeignKey(AutonomousRuntimeSession, null=True, blank=True, on_delete=models.SET_NULL, related_name='recommendations')
    target_tick = models.ForeignKey(AutonomousRuntimeTick, null=True, blank=True, on_delete=models.SET_NULL, related_name='recommendations')
    target_cadence_decision = models.ForeignKey(AutonomousCadenceDecision, null=True, blank=True, on_delete=models.SET_NULL, related_name='recommendations')
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.FloatField(default=0.5)
    blockers = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class AutonomousRunnerStatus(models.TextChoices):
    STOPPED = 'STOPPED', 'Stopped'
    RUNNING = 'RUNNING', 'Running'
    PAUSED = 'PAUSED', 'Paused'
    ERROR = 'ERROR', 'Error'


class AutonomousHeartbeatRunnerStatus(models.TextChoices):
    RUNNING = 'RUNNING', 'Running'
    IDLE = 'IDLE', 'Idle'
    PAUSED = 'PAUSED', 'Paused'
    BLOCKED = 'BLOCKED', 'Blocked'
    FAILED = 'FAILED', 'Failed'
    COMPLETED = 'COMPLETED', 'Completed'


class AutonomousHeartbeatDecisionType(models.TextChoices):
    RUN_DUE_TICK = 'RUN_DUE_TICK', 'Run due tick'
    WAIT_FOR_NEXT_WINDOW = 'WAIT_FOR_NEXT_WINDOW', 'Wait for next window'
    SKIP_FOR_COOLDOWN = 'SKIP_FOR_COOLDOWN', 'Skip for cooldown'
    PAUSE_SESSION = 'PAUSE_SESSION', 'Pause session'
    STOP_SESSION = 'STOP_SESSION', 'Stop session'
    BLOCK_SESSION = 'BLOCK_SESSION', 'Block session'


class AutonomousHeartbeatDecisionStatus(models.TextChoices):
    READY = 'READY', 'Ready'
    EXECUTED = 'EXECUTED', 'Executed'
    SKIPPED = 'SKIPPED', 'Skipped'
    BLOCKED = 'BLOCKED', 'Blocked'


class AutonomousTickDispatchStatus(models.TextChoices):
    QUEUED = 'QUEUED', 'Queued'
    STARTED = 'STARTED', 'Started'
    COMPLETED = 'COMPLETED', 'Completed'
    SKIPPED = 'SKIPPED', 'Skipped'
    BLOCKED = 'BLOCKED', 'Blocked'
    FAILED = 'FAILED', 'Failed'


class AutonomousHeartbeatRecommendationType(models.TextChoices):
    RUN_DUE_TICK_NOW = 'RUN_DUE_TICK_NOW', 'Run due tick now'
    WAIT_UNTIL_NEXT_DUE_WINDOW = 'WAIT_UNTIL_NEXT_DUE_WINDOW', 'Wait until next due window'
    SKIP_FOR_ACTIVE_COOLDOWN = 'SKIP_FOR_ACTIVE_COOLDOWN', 'Skip for active cooldown'
    PAUSE_FOR_RUNTIME_OR_SAFETY = 'PAUSE_FOR_RUNTIME_OR_SAFETY', 'Pause for runtime or safety'
    STOP_FOR_KILL_SWITCH = 'STOP_FOR_KILL_SWITCH', 'Stop for kill switch'
    REQUIRE_MANUAL_RUNNER_REVIEW = 'REQUIRE_MANUAL_RUNNER_REVIEW', 'Require manual runner review'


class AutonomousRunnerState(TimeStampedModel):
    runner_name = models.CharField(max_length=64, unique=True)
    runner_status = models.CharField(max_length=12, choices=AutonomousRunnerStatus.choices, default=AutonomousRunnerStatus.STOPPED)
    last_heartbeat_at = models.DateTimeField(null=True, blank=True)
    last_successful_run_at = models.DateTimeField(null=True, blank=True)
    last_error_at = models.DateTimeField(null=True, blank=True)
    active_session_count = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-updated_at', '-id']


class AutonomousHeartbeatRun(TimeStampedModel):
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    runner_status = models.CharField(max_length=12, choices=AutonomousHeartbeatRunnerStatus.choices, default=AutonomousHeartbeatRunnerStatus.RUNNING)
    considered_session_count = models.PositiveIntegerField(default=0)
    due_tick_count = models.PositiveIntegerField(default=0)
    executed_tick_count = models.PositiveIntegerField(default=0)
    wait_count = models.PositiveIntegerField(default=0)
    cooldown_skip_count = models.PositiveIntegerField(default=0)
    blocked_count = models.PositiveIntegerField(default=0)
    paused_count = models.PositiveIntegerField(default=0)
    stopped_count = models.PositiveIntegerField(default=0)
    recommendation_summary = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']


class AutonomousHeartbeatDecision(TimeStampedModel):
    linked_heartbeat_run = models.ForeignKey(AutonomousHeartbeatRun, on_delete=models.CASCADE, related_name='decisions')
    linked_session = models.ForeignKey(AutonomousRuntimeSession, on_delete=models.CASCADE, related_name='heartbeat_decisions')
    linked_latest_tick = models.ForeignKey(AutonomousRuntimeTick, null=True, blank=True, on_delete=models.SET_NULL, related_name='heartbeat_decisions')
    decision_type = models.CharField(max_length=24, choices=AutonomousHeartbeatDecisionType.choices)
    decision_status = models.CharField(max_length=12, choices=AutonomousHeartbeatDecisionStatus.choices, default=AutonomousHeartbeatDecisionStatus.READY)
    due_now = models.BooleanField(default=False)
    next_due_at = models.DateTimeField(null=True, blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    decision_summary = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class AutonomousTickDispatchAttempt(TimeStampedModel):
    linked_session = models.ForeignKey(AutonomousRuntimeSession, on_delete=models.CASCADE, related_name='tick_dispatch_attempts')
    linked_heartbeat_decision = models.ForeignKey(AutonomousHeartbeatDecision, on_delete=models.CASCADE, related_name='dispatch_attempts')
    linked_tick = models.ForeignKey(AutonomousRuntimeTick, null=True, blank=True, on_delete=models.SET_NULL, related_name='dispatch_attempts')
    dispatch_status = models.CharField(max_length=12, choices=AutonomousTickDispatchStatus.choices, default=AutonomousTickDispatchStatus.QUEUED)
    automatic = models.BooleanField(default=True)
    summary = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class AutonomousHeartbeatRecommendation(TimeStampedModel):
    recommendation_type = models.CharField(max_length=36, choices=AutonomousHeartbeatRecommendationType.choices)
    target_session = models.ForeignKey(AutonomousRuntimeSession, null=True, blank=True, on_delete=models.SET_NULL, related_name='heartbeat_recommendations')
    target_heartbeat_decision = models.ForeignKey(AutonomousHeartbeatDecision, null=True, blank=True, on_delete=models.SET_NULL, related_name='recommendations')
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.FloatField(default=0.5)
    blockers = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class AutonomousSessionTimingSnapshot(TimeStampedModel):
    linked_session = models.ForeignKey(AutonomousRuntimeSession, on_delete=models.CASCADE, related_name='timing_snapshots')
    linked_schedule_profile = models.ForeignKey(
        AutonomousScheduleProfile,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='timing_snapshots',
    )
    last_tick_at = models.DateTimeField(null=True, blank=True)
    next_due_at = models.DateTimeField(null=True, blank=True)
    active_cooldown_count = models.PositiveIntegerField(default=0)
    consecutive_no_action_ticks = models.PositiveIntegerField(default=0)
    consecutive_blocked_ticks = models.PositiveIntegerField(default=0)
    recent_dispatch_count = models.PositiveIntegerField(default=0)
    recent_loss_count = models.PositiveIntegerField(default=0)
    signal_pressure_state = models.CharField(max_length=12, choices=AutonomousSignalPressureState.choices, default=AutonomousSignalPressureState.NORMAL)
    timing_status = models.CharField(max_length=24, choices=AutonomousTimingStatus.choices, default=AutonomousTimingStatus.WAIT_SHORT)
    timing_summary = models.CharField(max_length=255, blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class AutonomousStopConditionEvaluation(TimeStampedModel):
    linked_session = models.ForeignKey(AutonomousRuntimeSession, on_delete=models.CASCADE, related_name='stop_condition_evaluations')
    evaluation_type = models.CharField(max_length=40, choices=AutonomousStopEvaluationType.choices)
    evaluation_status = models.CharField(max_length=12, choices=AutonomousStopEvaluationStatus.choices, default=AutonomousStopEvaluationStatus.INFO)
    evaluation_summary = models.CharField(max_length=255, blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class AutonomousTimingDecision(TimeStampedModel):
    linked_session = models.ForeignKey(AutonomousRuntimeSession, on_delete=models.CASCADE, related_name='timing_decisions')
    linked_timing_snapshot = models.ForeignKey(
        AutonomousSessionTimingSnapshot,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='timing_decisions',
    )
    decision_type = models.CharField(max_length=24, choices=AutonomousTimingDecisionType.choices)
    decision_status = models.CharField(max_length=12, choices=AutonomousTimingDecisionStatus.choices, default=AutonomousTimingDecisionStatus.PROPOSED)
    next_due_at = models.DateTimeField(null=True, blank=True)
    decision_summary = models.CharField(max_length=255, blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class AutonomousTimingRecommendation(TimeStampedModel):
    recommendation_type = models.CharField(max_length=48, choices=AutonomousTimingRecommendationType.choices)
    target_session = models.ForeignKey(AutonomousRuntimeSession, null=True, blank=True, on_delete=models.SET_NULL, related_name='timing_recommendations')
    target_timing_snapshot = models.ForeignKey(
        AutonomousSessionTimingSnapshot,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='recommendations',
    )
    target_timing_decision = models.ForeignKey(
        AutonomousTimingDecision,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='recommendations',
    )
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.FloatField(default=0.5)
    blockers = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class AutonomousProfileSelectionRun(TimeStampedModel):
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    considered_session_count = models.PositiveIntegerField(default=0)
    keep_current_profile_count = models.PositiveIntegerField(default=0)
    switch_recommended_count = models.PositiveIntegerField(default=0)
    switched_count = models.PositiveIntegerField(default=0)
    blocked_switch_count = models.PositiveIntegerField(default=0)
    recommendation_summary = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']


class AutonomousSessionContextReview(TimeStampedModel):
    linked_selection_run = models.ForeignKey(
        AutonomousProfileSelectionRun,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='context_reviews',
    )
    linked_session = models.ForeignKey(AutonomousRuntimeSession, on_delete=models.CASCADE, related_name='context_reviews')
    linked_current_profile = models.ForeignKey(
        AutonomousScheduleProfile,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='context_reviews',
    )
    linked_latest_timing_snapshot = models.ForeignKey(
        AutonomousSessionTimingSnapshot,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='context_reviews',
    )
    portfolio_pressure_state = models.CharField(
        max_length=20,
        choices=AutonomousProfilePortfolioPressureState.choices,
        default=AutonomousProfilePortfolioPressureState.NORMAL,
    )
    runtime_posture = models.CharField(
        max_length=12,
        choices=AutonomousProfileRuntimePosture.choices,
        default=AutonomousProfileRuntimePosture.NORMAL,
    )
    safety_posture = models.CharField(
        max_length=12,
        choices=AutonomousProfileSafetyPosture.choices,
        default=AutonomousProfileSafetyPosture.NORMAL,
    )
    signal_pressure_state = models.CharField(
        max_length=12,
        choices=AutonomousSignalPressureState.choices,
        default=AutonomousSignalPressureState.NORMAL,
    )
    recent_loss_state = models.CharField(
        max_length=16,
        choices=AutonomousRecentLossState.choices,
        default=AutonomousRecentLossState.NONE,
    )
    activity_state = models.CharField(
        max_length=20,
        choices=AutonomousProfileActivityState.choices,
        default=AutonomousProfileActivityState.ACTIVE,
    )
    context_status = models.CharField(
        max_length=40,
        choices=AutonomousProfileContextStatus.choices,
        default=AutonomousProfileContextStatus.STABLE,
    )
    context_summary = models.CharField(max_length=255, blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class AutonomousProfileSwitchDecision(TimeStampedModel):
    linked_selection_run = models.ForeignKey(
        AutonomousProfileSelectionRun,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='switch_decisions',
    )
    linked_session = models.ForeignKey(AutonomousRuntimeSession, on_delete=models.CASCADE, related_name='profile_switch_decisions')
    linked_context_review = models.ForeignKey(
        AutonomousSessionContextReview,
        on_delete=models.CASCADE,
        related_name='switch_decisions',
    )
    from_profile = models.ForeignKey(
        AutonomousScheduleProfile,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='switch_decisions_from',
    )
    to_profile = models.ForeignKey(
        AutonomousScheduleProfile,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='switch_decisions_to',
    )
    decision_type = models.CharField(max_length=40, choices=AutonomousProfileSwitchDecisionType.choices)
    decision_status = models.CharField(
        max_length=12,
        choices=AutonomousProfileSwitchDecisionStatus.choices,
        default=AutonomousProfileSwitchDecisionStatus.PROPOSED,
    )
    decision_summary = models.CharField(max_length=255, blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class AutonomousProfileSwitchRecord(TimeStampedModel):
    linked_selection_run = models.ForeignKey(
        AutonomousProfileSelectionRun,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='switch_records',
    )
    linked_session = models.ForeignKey(AutonomousRuntimeSession, on_delete=models.CASCADE, related_name='profile_switch_records')
    linked_switch_decision = models.ForeignKey(
        AutonomousProfileSwitchDecision,
        on_delete=models.CASCADE,
        related_name='switch_records',
    )
    previous_profile = models.ForeignKey(
        AutonomousScheduleProfile,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='switch_records_from',
    )
    applied_profile = models.ForeignKey(
        AutonomousScheduleProfile,
        on_delete=models.CASCADE,
        related_name='switch_records_to',
    )
    switch_status = models.CharField(max_length=12, choices=AutonomousProfileSwitchStatus.choices)
    switch_summary = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class AutonomousProfileRecommendation(TimeStampedModel):
    recommendation_type = models.CharField(max_length=44, choices=AutonomousProfileRecommendationType.choices)
    target_session = models.ForeignKey(
        AutonomousRuntimeSession,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='profile_recommendations',
    )
    target_context_review = models.ForeignKey(
        AutonomousSessionContextReview,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='recommendations',
    )
    target_switch_decision = models.ForeignKey(
        AutonomousProfileSwitchDecision,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='recommendations',
    )
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.FloatField(default=0.5)
    blockers = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class AutonomousSessionHealthStatus(models.TextChoices):
    HEALTHY = 'HEALTHY', 'Healthy'
    CAUTION = 'CAUTION', 'Caution'
    DEGRADED = 'DEGRADED', 'Degraded'
    BLOCKED = 'BLOCKED', 'Blocked'
    STALLED = 'STALLED', 'Stalled'


class AutonomousIncidentPressureState(models.TextChoices):
    NONE = 'NONE', 'None'
    CAUTION = 'CAUTION', 'Caution'
    HIGH = 'HIGH', 'High'


class AutonomousSessionAnomalyType(models.TextChoices):
    REPEATED_FAILED_TICKS = 'REPEATED_FAILED_TICKS', 'Repeated failed ticks'
    REPEATED_BLOCKED_TICKS = 'REPEATED_BLOCKED_TICKS', 'Repeated blocked ticks'
    RUNNER_SESSION_MISMATCH = 'RUNNER_SESSION_MISMATCH', 'Runner/session mismatch'
    STALE_SESSION_NO_PROGRESS = 'STALE_SESSION_NO_PROGRESS', 'Stale session no progress'
    PERSISTENT_PAUSE = 'PERSISTENT_PAUSE', 'Persistent pause'
    SAFETY_OR_RUNTIME_PRESSURE = 'SAFETY_OR_RUNTIME_PRESSURE', 'Safety or runtime pressure'
    INCIDENT_ESCALATION_PRESSURE = 'INCIDENT_ESCALATION_PRESSURE', 'Incident escalation pressure'
    POST_LOSS_STABILIZATION_REQUIRED = 'POST_LOSS_STABILIZATION_REQUIRED', 'Post-loss stabilization required'


class AutonomousSessionAnomalySeverity(models.TextChoices):
    INFO = 'INFO', 'Info'
    CAUTION = 'CAUTION', 'Caution'
    HIGH = 'HIGH', 'High'
    CRITICAL = 'CRITICAL', 'Critical'


class AutonomousSessionInterventionDecisionType(models.TextChoices):
    KEEP_RUNNING = 'KEEP_RUNNING', 'Keep running'
    PAUSE_SESSION = 'PAUSE_SESSION', 'Pause session'
    RESUME_SESSION = 'RESUME_SESSION', 'Resume session'
    STOP_SESSION = 'STOP_SESSION', 'Stop session'
    REQUIRE_MANUAL_REVIEW = 'REQUIRE_MANUAL_REVIEW', 'Require manual review'
    ESCALATE_TO_INCIDENT_REVIEW = 'ESCALATE_TO_INCIDENT_REVIEW', 'Escalate to incident review'


class AutonomousSessionInterventionDecisionStatus(models.TextChoices):
    PROPOSED = 'PROPOSED', 'Proposed'
    APPLIED = 'APPLIED', 'Applied'
    SKIPPED = 'SKIPPED', 'Skipped'
    BLOCKED = 'BLOCKED', 'Blocked'


class AutonomousSessionInterventionStatus(models.TextChoices):
    APPLIED = 'APPLIED', 'Applied'
    SKIPPED = 'SKIPPED', 'Skipped'
    BLOCKED = 'BLOCKED', 'Blocked'
    FAILED = 'FAILED', 'Failed'


class AutonomousSessionHealthRecommendationType(models.TextChoices):
    KEEP_SESSION_RUNNING = 'KEEP_SESSION_RUNNING', 'Keep session running'
    PAUSE_FOR_STABILIZATION = 'PAUSE_FOR_STABILIZATION', 'Pause for stabilization'
    STOP_FOR_PERSISTENT_BLOCKS = 'STOP_FOR_PERSISTENT_BLOCKS', 'Stop for persistent blocks'
    RESUME_AFTER_RECOVERY = 'RESUME_AFTER_RECOVERY', 'Resume after recovery'
    REQUIRE_MANUAL_HEALTH_REVIEW = 'REQUIRE_MANUAL_HEALTH_REVIEW', 'Require manual health review'
    ESCALATE_TO_INCIDENT_LAYER = 'ESCALATE_TO_INCIDENT_LAYER', 'Escalate to incident layer'


class AutonomousSessionRecoveryStatus(models.TextChoices):
    RECOVERED = 'RECOVERED', 'Recovered'
    PARTIALLY_RECOVERED = 'PARTIALLY_RECOVERED', 'Partially recovered'
    STILL_BLOCKED = 'STILL_BLOCKED', 'Still blocked'
    STABILIZING = 'STABILIZING', 'Stabilizing'
    UNRECOVERABLE = 'UNRECOVERABLE', 'Unrecoverable'


class AutonomousRecoveryBlockerType(models.TextChoices):
    SAFETY_BLOCK_ACTIVE = 'SAFETY_BLOCK_ACTIVE', 'Safety block active'
    RUNTIME_BLOCK_ACTIVE = 'RUNTIME_BLOCK_ACTIVE', 'Runtime block active'
    INCIDENT_PRESSURE_ACTIVE = 'INCIDENT_PRESSURE_ACTIVE', 'Incident pressure active'
    PORTFOLIO_PRESSURE_ACTIVE = 'PORTFOLIO_PRESSURE_ACTIVE', 'Portfolio pressure active'
    COOLDOWN_ACTIVE = 'COOLDOWN_ACTIVE', 'Cooldown active'
    RECENT_FAILURE_STREAK = 'RECENT_FAILURE_STREAK', 'Recent failure streak'
    RECENT_BLOCKED_STREAK = 'RECENT_BLOCKED_STREAK', 'Recent blocked streak'
    MANUAL_REVIEW_REQUIRED = 'MANUAL_REVIEW_REQUIRED', 'Manual review required'


class AutonomousRecoveryBlockerSeverity(models.TextChoices):
    INFO = 'INFO', 'Info'
    CAUTION = 'CAUTION', 'Caution'
    HIGH = 'HIGH', 'High'
    CRITICAL = 'CRITICAL', 'Critical'


class AutonomousResumeDecisionType(models.TextChoices):
    KEEP_PAUSED = 'KEEP_PAUSED', 'Keep paused'
    READY_TO_RESUME = 'READY_TO_RESUME', 'Ready to resume'
    RESUME_IN_MONITOR_ONLY_MODE = 'RESUME_IN_MONITOR_ONLY_MODE', 'Resume in monitor only mode'
    REQUIRE_MANUAL_RECOVERY_REVIEW = 'REQUIRE_MANUAL_RECOVERY_REVIEW', 'Require manual recovery review'
    STOP_SESSION_PERMANENTLY = 'STOP_SESSION_PERMANENTLY', 'Stop session permanently'
    ESCALATE_TO_INCIDENT_REVIEW = 'ESCALATE_TO_INCIDENT_REVIEW', 'Escalate to incident review'


class AutonomousResumeDecisionStatus(models.TextChoices):
    PROPOSED = 'PROPOSED', 'Proposed'
    SKIPPED = 'SKIPPED', 'Skipped'
    BLOCKED = 'BLOCKED', 'Blocked'


class AutonomousSessionRecoveryRecommendationType(models.TextChoices):
    RESUME_SESSION_SAFELY = 'RESUME_SESSION_SAFELY', 'Resume session safely'
    RESUME_IN_MONITOR_ONLY_MODE = 'RESUME_IN_MONITOR_ONLY_MODE', 'Resume in monitor only mode'
    KEEP_SESSION_PAUSED = 'KEEP_SESSION_PAUSED', 'Keep session paused'
    REQUIRE_MANUAL_RECOVERY_REVIEW = 'REQUIRE_MANUAL_RECOVERY_REVIEW', 'Require manual recovery review'
    STOP_SESSION_FOR_UNRECOVERABLE_STATE = 'STOP_SESSION_FOR_UNRECOVERABLE_STATE', 'Stop session for unrecoverable state'
    ESCALATE_RECOVERY_TO_INCIDENT_LAYER = 'ESCALATE_RECOVERY_TO_INCIDENT_LAYER', 'Escalate recovery to incident layer'


class AutonomousResumeStatus(models.TextChoices):
    APPLIED = 'APPLIED', 'Applied'
    SKIPPED = 'SKIPPED', 'Skipped'
    BLOCKED = 'BLOCKED', 'Blocked'
    FAILED = 'FAILED', 'Failed'


class AutonomousResumeApplyMode(models.TextChoices):
    MANUAL_RESUME = 'MANUAL_RESUME', 'Manual resume'
    AUTO_SAFE_RESUME = 'AUTO_SAFE_RESUME', 'Auto safe resume'
    MONITOR_ONLY_RESUME = 'MONITOR_ONLY_RESUME', 'Monitor only resume'


class AutonomousSessionHealthRun(TimeStampedModel):
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    considered_session_count = models.PositiveIntegerField(default=0)
    healthy_count = models.PositiveIntegerField(default=0)
    anomaly_count = models.PositiveIntegerField(default=0)
    pause_recommended_count = models.PositiveIntegerField(default=0)
    stop_recommended_count = models.PositiveIntegerField(default=0)
    resume_recommended_count = models.PositiveIntegerField(default=0)
    manual_review_count = models.PositiveIntegerField(default=0)
    intervention_applied_count = models.PositiveIntegerField(default=0)
    recommendation_summary = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']


class AutonomousSessionHealthSnapshot(TimeStampedModel):
    linked_health_run = models.ForeignKey(
        AutonomousSessionHealthRun,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='snapshots',
    )
    linked_session = models.ForeignKey(AutonomousRuntimeSession, on_delete=models.CASCADE, related_name='health_snapshots')
    linked_runner_state = models.ForeignKey(
        AutonomousRunnerState,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='health_snapshots',
    )
    linked_latest_tick = models.ForeignKey(
        AutonomousRuntimeTick,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='health_snapshots',
    )
    linked_latest_heartbeat_decision = models.ForeignKey(
        AutonomousHeartbeatDecision,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='health_snapshots',
    )
    linked_latest_timing_snapshot = models.ForeignKey(
        AutonomousSessionTimingSnapshot,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='health_snapshots',
    )
    session_health_status = models.CharField(max_length=12, choices=AutonomousSessionHealthStatus.choices, default=AutonomousSessionHealthStatus.HEALTHY)
    consecutive_failed_ticks = models.PositiveIntegerField(default=0)
    consecutive_blocked_ticks = models.PositiveIntegerField(default=0)
    consecutive_no_progress_ticks = models.PositiveIntegerField(default=0)
    has_active_cooldown = models.BooleanField(default=False)
    runner_session_mismatch = models.BooleanField(default=False)
    recent_dispatch_count = models.PositiveIntegerField(default=0)
    recent_outcome_close_count = models.PositiveIntegerField(default=0)
    recent_loss_count = models.PositiveIntegerField(default=0)
    incident_pressure_state = models.CharField(
        max_length=12,
        choices=AutonomousIncidentPressureState.choices,
        default=AutonomousIncidentPressureState.NONE,
    )
    health_summary = models.CharField(max_length=255, blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class AutonomousSessionAnomaly(TimeStampedModel):
    linked_session = models.ForeignKey(AutonomousRuntimeSession, on_delete=models.CASCADE, related_name='health_anomalies')
    linked_health_snapshot = models.ForeignKey(
        AutonomousSessionHealthSnapshot,
        on_delete=models.CASCADE,
        related_name='anomalies',
    )
    anomaly_type = models.CharField(max_length=40, choices=AutonomousSessionAnomalyType.choices)
    anomaly_severity = models.CharField(max_length=12, choices=AutonomousSessionAnomalySeverity.choices, default=AutonomousSessionAnomalySeverity.INFO)
    anomaly_summary = models.CharField(max_length=255, blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class AutonomousSessionInterventionDecision(TimeStampedModel):
    linked_session = models.ForeignKey(AutonomousRuntimeSession, on_delete=models.CASCADE, related_name='health_intervention_decisions')
    linked_health_snapshot = models.ForeignKey(
        AutonomousSessionHealthSnapshot,
        on_delete=models.CASCADE,
        related_name='intervention_decisions',
    )
    decision_type = models.CharField(max_length=36, choices=AutonomousSessionInterventionDecisionType.choices)
    decision_status = models.CharField(
        max_length=12,
        choices=AutonomousSessionInterventionDecisionStatus.choices,
        default=AutonomousSessionInterventionDecisionStatus.PROPOSED,
    )
    auto_applicable = models.BooleanField(default=False)
    decision_summary = models.CharField(max_length=255, blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class AutonomousSessionInterventionRecord(TimeStampedModel):
    linked_session = models.ForeignKey(AutonomousRuntimeSession, on_delete=models.CASCADE, related_name='health_intervention_records')
    linked_intervention_decision = models.ForeignKey(
        AutonomousSessionInterventionDecision,
        on_delete=models.CASCADE,
        related_name='records',
    )
    intervention_status = models.CharField(max_length=12, choices=AutonomousSessionInterventionStatus.choices)
    intervention_summary = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class AutonomousSessionHealthRecommendation(TimeStampedModel):
    recommendation_type = models.CharField(max_length=40, choices=AutonomousSessionHealthRecommendationType.choices)
    target_session = models.ForeignKey(
        AutonomousRuntimeSession,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='health_recommendations',
    )
    target_health_snapshot = models.ForeignKey(
        AutonomousSessionHealthSnapshot,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='recommendations',
    )
    target_intervention_decision = models.ForeignKey(
        AutonomousSessionInterventionDecision,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='recommendations',
    )
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.FloatField(default=0.5)
    blockers = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class AutonomousSessionRecoveryRun(TimeStampedModel):
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    considered_session_count = models.PositiveIntegerField(default=0)
    ready_to_resume_count = models.PositiveIntegerField(default=0)
    keep_paused_count = models.PositiveIntegerField(default=0)
    manual_review_count = models.PositiveIntegerField(default=0)
    stop_recommended_count = models.PositiveIntegerField(default=0)
    incident_escalation_count = models.PositiveIntegerField(default=0)
    recommendation_summary = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']


class AutonomousSessionRecoverySnapshot(TimeStampedModel):
    linked_recovery_run = models.ForeignKey(
        AutonomousSessionRecoveryRun,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='snapshots',
    )
    linked_session = models.ForeignKey(AutonomousRuntimeSession, on_delete=models.CASCADE, related_name='recovery_snapshots')
    linked_latest_health_snapshot = models.ForeignKey(
        AutonomousSessionHealthSnapshot,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='recovery_snapshots',
    )
    linked_latest_intervention_decision = models.ForeignKey(
        AutonomousSessionInterventionDecision,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='recovery_snapshots',
    )
    linked_latest_intervention_record = models.ForeignKey(
        AutonomousSessionInterventionRecord,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='recovery_snapshots',
    )
    linked_latest_timing_snapshot = models.ForeignKey(
        AutonomousSessionTimingSnapshot,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='recovery_snapshots',
    )
    recovery_status = models.CharField(
        max_length=24,
        choices=AutonomousSessionRecoveryStatus.choices,
        default=AutonomousSessionRecoveryStatus.STABILIZING,
    )
    safety_block_cleared = models.BooleanField(default=True)
    runtime_block_cleared = models.BooleanField(default=True)
    incident_pressure_cleared = models.BooleanField(default=True)
    portfolio_pressure_state = models.CharField(
        max_length=20,
        choices=AutonomousProfilePortfolioPressureState.choices,
        default=AutonomousProfilePortfolioPressureState.NORMAL,
    )
    cooldown_active = models.BooleanField(default=False)
    recent_failed_ticks = models.PositiveIntegerField(default=0)
    recent_blocked_ticks = models.PositiveIntegerField(default=0)
    recent_successful_ticks = models.PositiveIntegerField(default=0)
    recovery_summary = models.CharField(max_length=255, blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class AutonomousRecoveryBlocker(TimeStampedModel):
    linked_session = models.ForeignKey(AutonomousRuntimeSession, on_delete=models.CASCADE, related_name='recovery_blockers')
    linked_recovery_snapshot = models.ForeignKey(
        AutonomousSessionRecoverySnapshot,
        on_delete=models.CASCADE,
        related_name='blockers',
    )
    blocker_type = models.CharField(max_length=36, choices=AutonomousRecoveryBlockerType.choices)
    blocker_severity = models.CharField(
        max_length=12,
        choices=AutonomousRecoveryBlockerSeverity.choices,
        default=AutonomousRecoveryBlockerSeverity.INFO,
    )
    blocker_summary = models.CharField(max_length=255, blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class AutonomousResumeDecision(TimeStampedModel):
    linked_session = models.ForeignKey(AutonomousRuntimeSession, on_delete=models.CASCADE, related_name='resume_decisions')
    linked_recovery_snapshot = models.ForeignKey(
        AutonomousSessionRecoverySnapshot,
        on_delete=models.CASCADE,
        related_name='resume_decisions',
    )
    decision_type = models.CharField(max_length=40, choices=AutonomousResumeDecisionType.choices)
    decision_status = models.CharField(
        max_length=12,
        choices=AutonomousResumeDecisionStatus.choices,
        default=AutonomousResumeDecisionStatus.PROPOSED,
    )
    auto_applicable = models.BooleanField(default=False)
    decision_summary = models.CharField(max_length=255, blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class AutonomousSessionRecoveryRecommendation(TimeStampedModel):
    recommendation_type = models.CharField(max_length=48, choices=AutonomousSessionRecoveryRecommendationType.choices)
    target_session = models.ForeignKey(
        AutonomousRuntimeSession,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='recovery_recommendations',
    )
    target_recovery_snapshot = models.ForeignKey(
        AutonomousSessionRecoverySnapshot,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='recommendations',
    )
    target_resume_decision = models.ForeignKey(
        AutonomousResumeDecision,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='recommendations',
    )
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.FloatField(default=0.5)
    blockers = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class AutonomousResumeRecord(TimeStampedModel):
    linked_session = models.ForeignKey(AutonomousRuntimeSession, on_delete=models.CASCADE, related_name='resume_records')
    linked_resume_decision = models.ForeignKey(
        AutonomousResumeDecision,
        on_delete=models.CASCADE,
        related_name='records',
    )
    resume_status = models.CharField(max_length=12, choices=AutonomousResumeStatus.choices)
    applied_mode = models.CharField(max_length=24, choices=AutonomousResumeApplyMode.choices)
    resume_summary = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class AutonomousOpenPositionPressureState(models.TextChoices):
    NORMAL = 'NORMAL', 'Normal'
    CAUTION = 'CAUTION', 'Caution'
    THROTTLED = 'THROTTLED', 'Throttled'
    BLOCK_NEW_ACTIVITY = 'BLOCK_NEW_ACTIVITY', 'Block new activity'


class AutonomousGlobalRuntimePosture(models.TextChoices):
    NORMAL = 'NORMAL', 'Normal'
    CAUTION = 'CAUTION', 'Caution'
    BLOCKED = 'BLOCKED', 'Blocked'


class AutonomousGlobalSafetyPosture(models.TextChoices):
    NORMAL = 'NORMAL', 'Normal'
    CAUTION = 'CAUTION', 'Caution'
    HARD_BLOCK = 'HARD_BLOCK', 'Hard block'


class AutonomousCapacityStatus(models.TextChoices):
    AVAILABLE = 'AVAILABLE', 'Available'
    LIMITED = 'LIMITED', 'Limited'
    THROTTLED = 'THROTTLED', 'Throttled'
    BLOCKED = 'BLOCKED', 'Blocked'


class AutonomousSessionPriorityState(models.TextChoices):
    HIGH_VALUE = 'HIGH_VALUE', 'High value'
    MEDIUM_VALUE = 'MEDIUM_VALUE', 'Medium value'
    LOW_VALUE = 'LOW_VALUE', 'Low value'
    NO_VALUE = 'NO_VALUE', 'No value'


class AutonomousSessionOperabilityState(models.TextChoices):
    READY = 'READY', 'Ready'
    RECOVERABLE = 'RECOVERABLE', 'Recoverable'
    CAUTION = 'CAUTION', 'Caution'
    BLOCKED = 'BLOCKED', 'Blocked'
    RETIRE_CANDIDATE = 'RETIRE_CANDIDATE', 'Retire candidate'


class AutonomousSessionAdmissionStatus(models.TextChoices):
    ADMIT = 'ADMIT', 'Admit'
    RESUME_ALLOWED = 'RESUME_ALLOWED', 'Resume allowed'
    PARK = 'PARK', 'Park'
    DEFER = 'DEFER', 'Defer'
    PAUSE = 'PAUSE', 'Pause'
    RETIRE = 'RETIRE', 'Retire'
    MANUAL_REVIEW = 'MANUAL_REVIEW', 'Manual review'


class AutonomousSessionAdmissionDecisionType(models.TextChoices):
    ADMIT_SESSION = 'ADMIT_SESSION', 'Admit session'
    ALLOW_RESUME = 'ALLOW_RESUME', 'Allow resume'
    PARK_SESSION = 'PARK_SESSION', 'Park session'
    DEFER_SESSION = 'DEFER_SESSION', 'Defer session'
    PAUSE_SESSION = 'PAUSE_SESSION', 'Pause session'
    RETIRE_SESSION = 'RETIRE_SESSION', 'Retire session'
    REQUIRE_MANUAL_ADMISSION_REVIEW = 'REQUIRE_MANUAL_ADMISSION_REVIEW', 'Require manual review'


class AutonomousSessionAdmissionDecisionStatus(models.TextChoices):
    PROPOSED = 'PROPOSED', 'Proposed'
    APPLIED = 'APPLIED', 'Applied'
    SKIPPED = 'SKIPPED', 'Skipped'
    BLOCKED = 'BLOCKED', 'Blocked'


class AutonomousSessionAdmissionRecommendationType(models.TextChoices):
    ADMIT_HIGH_PRIORITY_SESSION = 'ADMIT_HIGH_PRIORITY_SESSION', 'Admit high priority session'
    ALLOW_SAFE_RESUME = 'ALLOW_SAFE_RESUME', 'Allow safe resume'
    PARK_LOW_SIGNAL_SESSION = 'PARK_LOW_SIGNAL_SESSION', 'Park low signal session'
    DEFER_FOR_CAPACITY_PRESSURE = 'DEFER_FOR_CAPACITY_PRESSURE', 'Defer for capacity pressure'
    PAUSE_FOR_GLOBAL_THROTTLE = 'PAUSE_FOR_GLOBAL_THROTTLE', 'Pause for global throttle'
    RETIRE_LOW_VALUE_SESSION = 'RETIRE_LOW_VALUE_SESSION', 'Retire low value session'
    REQUIRE_MANUAL_ADMISSION_REVIEW = 'REQUIRE_MANUAL_ADMISSION_REVIEW', 'Require manual admission review'


class AutonomousSessionAdmissionRun(TimeStampedModel):
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    considered_session_count = models.PositiveIntegerField(default=0)
    admitted_count = models.PositiveIntegerField(default=0)
    resume_allowed_count = models.PositiveIntegerField(default=0)
    parked_count = models.PositiveIntegerField(default=0)
    deferred_count = models.PositiveIntegerField(default=0)
    paused_count = models.PositiveIntegerField(default=0)
    retired_count = models.PositiveIntegerField(default=0)
    manual_review_count = models.PositiveIntegerField(default=0)
    recommendation_summary = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']


class AutonomousGlobalCapacitySnapshot(TimeStampedModel):
    linked_admission_run = models.ForeignKey(AutonomousSessionAdmissionRun, null=True, blank=True, on_delete=models.SET_NULL, related_name='capacity_snapshots')
    max_active_sessions = models.PositiveIntegerField(default=1)
    current_running_sessions = models.PositiveIntegerField(default=0)
    current_paused_sessions = models.PositiveIntegerField(default=0)
    current_degraded_sessions = models.PositiveIntegerField(default=0)
    current_blocked_sessions = models.PositiveIntegerField(default=0)
    active_dispatch_load = models.PositiveIntegerField(default=0)
    open_position_pressure_state = models.CharField(max_length=24, choices=AutonomousOpenPositionPressureState.choices, default=AutonomousOpenPositionPressureState.NORMAL)
    runtime_posture = models.CharField(max_length=12, choices=AutonomousGlobalRuntimePosture.choices, default=AutonomousGlobalRuntimePosture.NORMAL)
    safety_posture = models.CharField(max_length=12, choices=AutonomousGlobalSafetyPosture.choices, default=AutonomousGlobalSafetyPosture.NORMAL)
    incident_pressure_state = models.CharField(max_length=12, choices=AutonomousIncidentPressureState.choices, default=AutonomousIncidentPressureState.NONE)
    capacity_status = models.CharField(max_length=12, choices=AutonomousCapacityStatus.choices, default=AutonomousCapacityStatus.AVAILABLE)
    snapshot_summary = models.CharField(max_length=255, blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class AutonomousSessionAdmissionReview(TimeStampedModel):
    linked_admission_run = models.ForeignKey(AutonomousSessionAdmissionRun, null=True, blank=True, on_delete=models.SET_NULL, related_name='reviews')
    linked_session = models.ForeignKey(AutonomousRuntimeSession, on_delete=models.CASCADE, related_name='admission_reviews')
    linked_capacity_snapshot = models.ForeignKey(AutonomousGlobalCapacitySnapshot, on_delete=models.CASCADE, related_name='session_reviews')
    linked_latest_health_snapshot = models.ForeignKey(AutonomousSessionHealthSnapshot, null=True, blank=True, on_delete=models.SET_NULL, related_name='admission_reviews')
    linked_latest_recovery_snapshot = models.ForeignKey(AutonomousSessionRecoverySnapshot, null=True, blank=True, on_delete=models.SET_NULL, related_name='admission_reviews')
    linked_latest_context_review = models.ForeignKey(AutonomousSessionContextReview, null=True, blank=True, on_delete=models.SET_NULL, related_name='admission_reviews')
    linked_current_profile = models.ForeignKey(AutonomousScheduleProfile, null=True, blank=True, on_delete=models.SET_NULL, related_name='admission_reviews')
    session_priority_state = models.CharField(max_length=16, choices=AutonomousSessionPriorityState.choices, default=AutonomousSessionPriorityState.MEDIUM_VALUE)
    session_operability_state = models.CharField(max_length=20, choices=AutonomousSessionOperabilityState.choices, default=AutonomousSessionOperabilityState.CAUTION)
    admission_status = models.CharField(max_length=16, choices=AutonomousSessionAdmissionStatus.choices, default=AutonomousSessionAdmissionStatus.DEFER)
    review_summary = models.CharField(max_length=255, blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class AutonomousSessionAdmissionDecision(TimeStampedModel):
    linked_session = models.ForeignKey(AutonomousRuntimeSession, on_delete=models.CASCADE, related_name='admission_decisions')
    linked_admission_review = models.ForeignKey(AutonomousSessionAdmissionReview, on_delete=models.CASCADE, related_name='decisions')
    decision_type = models.CharField(max_length=40, choices=AutonomousSessionAdmissionDecisionType.choices)
    decision_status = models.CharField(max_length=12, choices=AutonomousSessionAdmissionDecisionStatus.choices, default=AutonomousSessionAdmissionDecisionStatus.PROPOSED)
    auto_applicable = models.BooleanField(default=False)
    decision_summary = models.CharField(max_length=255, blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class AutonomousSessionAdmissionRecommendation(TimeStampedModel):
    recommendation_type = models.CharField(max_length=48, choices=AutonomousSessionAdmissionRecommendationType.choices)
    target_session = models.ForeignKey(AutonomousRuntimeSession, null=True, blank=True, on_delete=models.SET_NULL, related_name='admission_recommendations')
    target_admission_review = models.ForeignKey(AutonomousSessionAdmissionReview, null=True, blank=True, on_delete=models.SET_NULL, related_name='recommendations')
    target_admission_decision = models.ForeignKey(AutonomousSessionAdmissionDecision, null=True, blank=True, on_delete=models.SET_NULL, related_name='recommendations')
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.FloatField(default=0.5)
    blockers = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class GovernanceReviewSourceModule(models.TextChoices):
    RUNTIME_GOVERNOR = 'runtime_governor', 'Runtime governor'
    MISSION_CONTROL = 'mission_control', 'Mission control'
    PORTFOLIO_GOVERNOR = 'portfolio_governor', 'Portfolio governor'


class GovernanceReviewSourceType(models.TextChoices):
    MODE_FEEDBACK_APPLY = 'mode_feedback_apply', 'Mode feedback apply'
    MODE_STABILIZATION = 'mode_stabilization', 'Mode stabilization'
    SESSION_HEALTH = 'session_health', 'Session health'
    SESSION_RECOVERY = 'session_recovery', 'Session recovery'
    SESSION_ADMISSION = 'session_admission', 'Session admission'
    EXPOSURE_COORDINATION = 'exposure_coordination', 'Exposure coordination'
    EXPOSURE_APPLY = 'exposure_apply', 'Exposure apply'


class GovernanceReviewItemStatus(models.TextChoices):
    OPEN = 'OPEN', 'Open'
    IN_REVIEW = 'IN_REVIEW', 'In review'
    RESOLVED = 'RESOLVED', 'Resolved'
    DISMISSED = 'DISMISSED', 'Dismissed'


class GovernanceReviewSeverity(models.TextChoices):
    INFO = 'INFO', 'Info'
    CAUTION = 'CAUTION', 'Caution'
    HIGH = 'HIGH', 'High'
    CRITICAL = 'CRITICAL', 'Critical'


class GovernanceReviewPriority(models.TextChoices):
    P1 = 'P1', 'P1'
    P2 = 'P2', 'P2'
    P3 = 'P3', 'P3'
    P4 = 'P4', 'P4'


class GovernanceReviewRecommendationType(models.TextChoices):
    REVIEW_NOW = 'REVIEW_NOW', 'Review now'
    SAFE_TO_DISMISS = 'SAFE_TO_DISMISS', 'Safe to dismiss'
    RETRY_LATER = 'RETRY_LATER', 'Retry later'
    REQUIRE_OPERATOR_CONFIRMATION = 'REQUIRE_OPERATOR_CONFIRMATION', 'Require operator confirmation'
    ESCALATE_PRIORITY = 'ESCALATE_PRIORITY', 'Escalate priority'


class GovernanceReviewQueueRun(TimeStampedModel):
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    collected_item_count = models.PositiveIntegerField(default=0)
    high_priority_count = models.PositiveIntegerField(default=0)
    blocked_count = models.PositiveIntegerField(default=0)
    deferred_count = models.PositiveIntegerField(default=0)
    manual_review_count = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']


class GovernanceReviewItem(TimeStampedModel):
    source_module = models.CharField(max_length=32, choices=GovernanceReviewSourceModule.choices)
    source_type = models.CharField(max_length=32, choices=GovernanceReviewSourceType.choices)
    source_object_id = models.PositiveIntegerField()
    item_status = models.CharField(max_length=12, choices=GovernanceReviewItemStatus.choices, default=GovernanceReviewItemStatus.OPEN)
    severity = models.CharField(max_length=12, choices=GovernanceReviewSeverity.choices, default=GovernanceReviewSeverity.CAUTION)
    queue_priority = models.CharField(max_length=2, choices=GovernanceReviewPriority.choices, default=GovernanceReviewPriority.P3)
    linked_session = models.ForeignKey(
        AutonomousRuntimeSession,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='governance_review_items',
    )
    linked_market = models.ForeignKey(
        'markets.Market',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='governance_review_items',
    )
    title = models.CharField(max_length=255)
    summary = models.CharField(max_length=255, blank=True)
    blockers = models.JSONField(default=list, blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['queue_priority', '-updated_at', '-id']
        constraints = [
            models.UniqueConstraint(
                fields=['source_module', 'source_type', 'source_object_id'],
                name='governance_review_item_source_unique',
            ),
        ]


class GovernanceReviewRecommendation(TimeStampedModel):
    linked_review_item = models.ForeignKey(
        GovernanceReviewItem,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='recommendations',
    )
    recommendation_type = models.CharField(max_length=40, choices=GovernanceReviewRecommendationType.choices)
    rationale = models.CharField(max_length=255)
    confidence = models.FloatField(default=0.5)
    blockers = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at', '-id']


class GovernanceReviewResolutionType(models.TextChoices):
    APPLY_MANUAL_APPROVAL = 'APPLY_MANUAL_APPROVAL', 'Apply manual approval'
    KEEP_BLOCKED = 'KEEP_BLOCKED', 'Keep blocked'
    DISMISS_AS_EXPECTED = 'DISMISS_AS_EXPECTED', 'Dismiss as expected'
    REQUIRE_FOLLOWUP = 'REQUIRE_FOLLOWUP', 'Require follow-up'
    RETRY_SAFE_APPLY = 'RETRY_SAFE_APPLY', 'Retry safe apply'


class GovernanceReviewResolutionStatus(models.TextChoices):
    APPLIED = 'APPLIED', 'Applied'
    SKIPPED = 'SKIPPED', 'Skipped'
    BLOCKED = 'BLOCKED', 'Blocked'
    FAILED = 'FAILED', 'Failed'


class GovernanceReviewResolution(TimeStampedModel):
    linked_review_item = models.ForeignKey(
        GovernanceReviewItem,
        on_delete=models.CASCADE,
        related_name='resolutions',
    )
    resolution_type = models.CharField(max_length=32, choices=GovernanceReviewResolutionType.choices)
    resolution_status = models.CharField(max_length=12, choices=GovernanceReviewResolutionStatus.choices)
    resolution_summary = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at', '-id']


class GovernanceAutoResolutionDecisionType(models.TextChoices):
    AUTO_DISMISS = 'AUTO_DISMISS', 'Auto dismiss'
    AUTO_RETRY_SAFE_APPLY = 'AUTO_RETRY_SAFE_APPLY', 'Auto retry safe apply'
    AUTO_REQUIRE_FOLLOWUP = 'AUTO_REQUIRE_FOLLOWUP', 'Auto require follow-up'
    DO_NOT_AUTO_RESOLVE = 'DO_NOT_AUTO_RESOLVE', 'Do not auto-resolve'


class GovernanceAutoResolutionDecisionStatus(models.TextChoices):
    PROPOSED = 'PROPOSED', 'Proposed'
    APPLIED = 'APPLIED', 'Applied'
    SKIPPED = 'SKIPPED', 'Skipped'
    BLOCKED = 'BLOCKED', 'Blocked'


class GovernanceAutoResolutionRecordStatus(models.TextChoices):
    APPLIED = 'APPLIED', 'Applied'
    SKIPPED = 'SKIPPED', 'Skipped'
    BLOCKED = 'BLOCKED', 'Blocked'
    FAILED = 'FAILED', 'Failed'


class GovernanceAutoResolutionEffectType(models.TextChoices):
    DISMISSED = 'DISMISSED', 'Dismissed'
    RETRY_SAFE_APPLY_TRIGGERED = 'RETRY_SAFE_APPLY_TRIGGERED', 'Retry safe apply triggered'
    FOLLOWUP_MARKED = 'FOLLOWUP_MARKED', 'Follow-up marked'
    NO_CHANGE = 'NO_CHANGE', 'No change'


class GovernanceQueueAgeBucket(models.TextChoices):
    FRESH = 'FRESH', 'Fresh'
    AGING = 'AGING', 'Aging'
    STALE = 'STALE', 'Stale'
    OVERDUE = 'OVERDUE', 'Overdue'


class GovernanceQueueAgingStatus(models.TextChoices):
    NORMAL = 'NORMAL', 'Normal'
    PRIORITY_ESCALATION = 'PRIORITY_ESCALATION', 'Priority escalation'
    FOLLOWUP_DUE = 'FOLLOWUP_DUE', 'Follow-up due'
    STALE_BLOCKED = 'STALE_BLOCKED', 'Stale blocked'
    MANUAL_REVIEW_OVERDUE = 'MANUAL_REVIEW_OVERDUE', 'Manual review overdue'


class GovernanceQueueAgingRecommendationType(models.TextChoices):
    KEEP_PRIORITY = 'KEEP_PRIORITY', 'Keep priority'
    ESCALATE_TO_P1 = 'ESCALATE_TO_P1', 'Escalate to P1'
    ESCALATE_TO_P2 = 'ESCALATE_TO_P2', 'Escalate to P2'
    REQUIRE_FOLLOWUP_NOW = 'REQUIRE_FOLLOWUP_NOW', 'Require follow-up now'
    ESCALATE_BLOCKED_ITEM = 'ESCALATE_BLOCKED_ITEM', 'Escalate blocked item'
    REQUIRE_OPERATOR_REVIEW_NOW = 'REQUIRE_OPERATOR_REVIEW_NOW', 'Require operator review now'


class GovernanceQueueAgingRun(TimeStampedModel):
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    considered_item_count = models.PositiveIntegerField(default=0)
    stale_item_count = models.PositiveIntegerField(default=0)
    escalated_count = models.PositiveIntegerField(default=0)
    followup_due_count = models.PositiveIntegerField(default=0)
    blocked_stale_count = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']


class GovernanceQueueAgingReview(TimeStampedModel):
    linked_review_item = models.ForeignKey(
        GovernanceReviewItem,
        on_delete=models.CASCADE,
        related_name='aging_reviews',
    )
    linked_aging_run = models.ForeignKey(
        GovernanceQueueAgingRun,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='reviews',
    )
    age_bucket = models.CharField(max_length=12, choices=GovernanceQueueAgeBucket.choices, default=GovernanceQueueAgeBucket.FRESH)
    aging_status = models.CharField(max_length=32, choices=GovernanceQueueAgingStatus.choices, default=GovernanceQueueAgingStatus.NORMAL)
    review_summary = models.CharField(max_length=255, blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at', '-id']


class GovernanceQueueAgingRecommendation(TimeStampedModel):
    linked_review_item = models.ForeignKey(
        GovernanceReviewItem,
        on_delete=models.CASCADE,
        related_name='aging_recommendations',
    )
    linked_aging_review = models.ForeignKey(
        GovernanceQueueAgingReview,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='recommendations',
    )
    recommendation_type = models.CharField(max_length=48, choices=GovernanceQueueAgingRecommendationType.choices)
    rationale = models.CharField(max_length=255)
    confidence = models.FloatField(default=0.5)
    blockers = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at', '-id']


class GovernanceAutoResolutionRun(TimeStampedModel):
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    considered_item_count = models.PositiveIntegerField(default=0)
    eligible_count = models.PositiveIntegerField(default=0)
    applied_count = models.PositiveIntegerField(default=0)
    skipped_count = models.PositiveIntegerField(default=0)
    blocked_count = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']


class GovernanceAutoResolutionDecision(TimeStampedModel):
    linked_review_item = models.ForeignKey(
        GovernanceReviewItem,
        on_delete=models.CASCADE,
        related_name='auto_resolution_decisions',
    )
    linked_auto_resolution_run = models.ForeignKey(
        GovernanceAutoResolutionRun,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='decisions',
    )
    decision_type = models.CharField(max_length=32, choices=GovernanceAutoResolutionDecisionType.choices)
    decision_status = models.CharField(
        max_length=12,
        choices=GovernanceAutoResolutionDecisionStatus.choices,
        default=GovernanceAutoResolutionDecisionStatus.PROPOSED,
    )
    auto_applicable = models.BooleanField(default=False)
    decision_summary = models.CharField(max_length=255, blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at', '-id']


class GovernanceAutoResolutionRecord(TimeStampedModel):
    linked_review_item = models.ForeignKey(
        GovernanceReviewItem,
        on_delete=models.CASCADE,
        related_name='auto_resolution_records',
    )
    linked_auto_resolution_decision = models.ForeignKey(
        GovernanceAutoResolutionDecision,
        on_delete=models.CASCADE,
        related_name='records',
    )
    record_status = models.CharField(max_length=12, choices=GovernanceAutoResolutionRecordStatus.choices)
    effect_type = models.CharField(max_length=32, choices=GovernanceAutoResolutionEffectType.choices)
    record_summary = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at', '-id']

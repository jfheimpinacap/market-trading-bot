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

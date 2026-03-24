from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel


class SessionStatus(models.TextChoices):
    IDLE = 'IDLE', 'Idle'
    RUNNING = 'RUNNING', 'Running'
    PAUSED = 'PAUSED', 'Paused'
    STOPPED = 'STOPPED', 'Stopped'
    FAILED = 'FAILED', 'Failed'


class CycleStatus(models.TextChoices):
    SUCCESS = 'SUCCESS', 'Success'
    PARTIAL = 'PARTIAL', 'Partial'
    FAILED = 'FAILED', 'Failed'
    SKIPPED = 'SKIPPED', 'Skipped'


class RuntimeStatus(models.TextChoices):
    IDLE = 'IDLE', 'Idle'
    RUNNING = 'RUNNING', 'Running'
    PAUSED = 'PAUSED', 'Paused'
    STOPPED = 'STOPPED', 'Stopped'


class ContinuousDemoSession(TimeStampedModel):
    session_status = models.CharField(max_length=12, choices=SessionStatus.choices, default=SessionStatus.IDLE)
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)
    last_cycle_at = models.DateTimeField(null=True, blank=True)
    total_cycles = models.PositiveIntegerField(default=0)
    total_auto_executed = models.PositiveIntegerField(default=0)
    total_pending_approvals = models.PositiveIntegerField(default=0)
    total_blocked = models.PositiveIntegerField(default=0)
    total_errors = models.PositiveIntegerField(default=0)
    summary = models.CharField(max_length=255, blank=True)
    settings_snapshot = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']


class ContinuousDemoCycleRun(TimeStampedModel):
    session = models.ForeignKey(ContinuousDemoSession, on_delete=models.CASCADE, related_name='cycles')
    cycle_number = models.PositiveIntegerField()
    status = models.CharField(max_length=12, choices=CycleStatus.choices, default=CycleStatus.SUCCESS)
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)
    actions_run = models.JSONField(default=list, blank=True)
    markets_evaluated = models.PositiveIntegerField(default=0)
    proposals_generated = models.PositiveIntegerField(default=0)
    auto_executed_count = models.PositiveIntegerField(default=0)
    approval_required_count = models.PositiveIntegerField(default=0)
    blocked_count = models.PositiveIntegerField(default=0)
    summary = models.CharField(max_length=255, blank=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']
        constraints = [
            models.UniqueConstraint(fields=['session', 'cycle_number'], name='continuous_demo_session_cycle_number_uniq'),
        ]


class LoopRuntimeControl(TimeStampedModel):
    runtime_status = models.CharField(max_length=12, choices=RuntimeStatus.choices, default=RuntimeStatus.IDLE)
    enabled = models.BooleanField(default=True)
    kill_switch = models.BooleanField(default=False)
    stop_requested = models.BooleanField(default=False)
    pause_requested = models.BooleanField(default=False)
    cycle_in_progress = models.BooleanField(default=False)
    last_heartbeat_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    active_session = models.ForeignKey(ContinuousDemoSession, null=True, blank=True, on_delete=models.SET_NULL, related_name='runtime_records')
    default_settings = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['id']

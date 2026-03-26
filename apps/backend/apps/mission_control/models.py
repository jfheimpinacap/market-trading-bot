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

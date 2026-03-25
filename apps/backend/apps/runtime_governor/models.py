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

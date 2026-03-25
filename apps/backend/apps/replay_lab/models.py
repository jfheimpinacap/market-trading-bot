from decimal import Decimal

from django.db import models

from apps.common.models import TimeStampedModel
from apps.paper_trading.models import PaperAccount


class ReplayRunStatus(models.TextChoices):
    READY = 'READY', 'Ready'
    RUNNING = 'RUNNING', 'Running'
    SUCCESS = 'SUCCESS', 'Success'
    PARTIAL = 'PARTIAL', 'Partial'
    FAILED = 'FAILED', 'Failed'


class ReplaySourceScope(models.TextChoices):
    REAL_ONLY = 'real_only', 'Real only'
    DEMO_ONLY = 'demo_only', 'Demo only'
    MIXED = 'mixed', 'Mixed'


class ReplayRun(TimeStampedModel):
    status = models.CharField(max_length=16, choices=ReplayRunStatus.choices, default=ReplayRunStatus.READY)
    source_scope = models.CharField(max_length=16, choices=ReplaySourceScope.choices, default=ReplaySourceScope.REAL_ONLY)
    provider_scope = models.CharField(max_length=64, blank=True, default='all')
    replay_start_at = models.DateTimeField()
    replay_end_at = models.DateTimeField()
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    snapshots_considered = models.PositiveIntegerField(default=0)
    markets_considered = models.PositiveIntegerField(default=0)
    proposals_generated = models.PositiveIntegerField(default=0)
    trades_executed = models.PositiveIntegerField(default=0)
    approvals_required = models.PositiveIntegerField(default=0)
    blocked_count = models.PositiveIntegerField(default=0)

    total_pnl = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    ending_equity = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    summary = models.CharField(max_length=255, blank=True)
    details = models.JSONField(default=dict, blank=True)

    paper_account = models.ForeignKey(PaperAccount, null=True, blank=True, on_delete=models.SET_NULL, related_name='replay_runs')

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['source_scope', '-created_at']),
            models.Index(fields=['provider_scope', '-created_at']),
        ]


class ReplayStep(TimeStampedModel):
    replay_run = models.ForeignKey(ReplayRun, on_delete=models.CASCADE, related_name='steps')
    step_index = models.PositiveIntegerField()
    step_timestamp = models.DateTimeField()
    snapshots_used = models.PositiveIntegerField(default=0)
    markets_considered = models.PositiveIntegerField(default=0)
    proposals_generated = models.PositiveIntegerField(default=0)
    trades_executed = models.PositiveIntegerField(default=0)
    approvals_required = models.PositiveIntegerField(default=0)
    blocked_count = models.PositiveIntegerField(default=0)
    estimated_equity = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    notes = models.CharField(max_length=255, blank=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['step_index', 'id']
        constraints = [
            models.UniqueConstraint(fields=['replay_run', 'step_index'], name='replay_step_run_index_uniq'),
        ]
        indexes = [
            models.Index(fields=['replay_run', 'step_index']),
            models.Index(fields=['step_timestamp']),
        ]

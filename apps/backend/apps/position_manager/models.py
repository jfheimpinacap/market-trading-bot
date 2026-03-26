from django.db import models

from apps.common.models import TimeStampedModel
from apps.paper_trading.models import PaperPosition
from apps.risk_agent.models import PositionWatchEvent


class PositionLifecycleStatus(models.TextChoices):
    HOLD = 'HOLD', 'Hold'
    REDUCE = 'REDUCE', 'Reduce'
    CLOSE = 'CLOSE', 'Close'
    REVIEW_REQUIRED = 'REVIEW_REQUIRED', 'Review required'
    BLOCK_ADD = 'BLOCK_ADD', 'Block add'
    EXPIRED = 'EXPIRED', 'Expired'


class PositionLifecycleRunStatus(models.TextChoices):
    READY = 'READY', 'Ready'
    SUCCESS = 'SUCCESS', 'Success'
    FAILED = 'FAILED', 'Failed'


class PositionLifecycleRun(TimeStampedModel):
    status = models.CharField(max_length=12, choices=PositionLifecycleRunStatus.choices, default=PositionLifecycleRunStatus.READY)
    watched_positions = models.PositiveIntegerField(default=0)
    decisions_count = models.PositiveIntegerField(default=0)
    hold_count = models.PositiveIntegerField(default=0)
    reduce_count = models.PositiveIntegerField(default=0)
    close_count = models.PositiveIntegerField(default=0)
    review_required_count = models.PositiveIntegerField(default=0)
    summary = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class PositionLifecycleDecision(TimeStampedModel):
    run = models.ForeignKey(PositionLifecycleRun, on_delete=models.CASCADE, related_name='decisions')
    paper_position = models.ForeignKey(PaperPosition, on_delete=models.SET_NULL, null=True, blank=True, related_name='lifecycle_decisions')
    latest_watch_event = models.ForeignKey(PositionWatchEvent, on_delete=models.SET_NULL, null=True, blank=True, related_name='lifecycle_decisions')
    status = models.CharField(max_length=24, choices=PositionLifecycleStatus.choices)
    decision_confidence = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    rationale = models.TextField(blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    risk_context = models.JSONField(default=dict, blank=True)
    prediction_context = models.JSONField(default=dict, blank=True)
    narrative_context = models.JSONField(default=dict, blank=True)
    position_snapshot = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class PositionExitPlan(TimeStampedModel):
    decision = models.OneToOneField(PositionLifecycleDecision, on_delete=models.CASCADE, related_name='exit_plan')
    paper_position = models.ForeignKey(PaperPosition, on_delete=models.SET_NULL, null=True, blank=True, related_name='exit_plans')
    action = models.CharField(max_length=24, choices=PositionLifecycleStatus.choices)
    target_quantity = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    quantity_delta = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    execution_mode = models.CharField(max_length=24, default='paper_only')
    queue_required = models.BooleanField(default=False)
    auto_execute_allowed = models.BooleanField(default=False)
    final_recommended_action = models.CharField(max_length=24, choices=PositionLifecycleStatus.choices)
    execution_path = models.CharField(max_length=48, default='record_only')
    explanation = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']

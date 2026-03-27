from django.db import models

from apps.common.models import TimeStampedModel


class RunbookTemplate(TimeStampedModel):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=120, unique=True)
    trigger_type = models.CharField(max_length=80)
    description = models.TextField(blank=True)
    severity_hint = models.CharField(max_length=24, blank=True)
    is_enabled = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['name', 'id']


class RunbookInstanceStatus(models.TextChoices):
    OPEN = 'OPEN', 'Open'
    IN_PROGRESS = 'IN_PROGRESS', 'In progress'
    BLOCKED = 'BLOCKED', 'Blocked'
    COMPLETED = 'COMPLETED', 'Completed'
    ABORTED = 'ABORTED', 'Aborted'
    ESCALATED = 'ESCALATED', 'Escalated'


class RunbookPriority(models.TextChoices):
    LOW = 'LOW', 'Low'
    MEDIUM = 'MEDIUM', 'Medium'
    HIGH = 'HIGH', 'High'
    CRITICAL = 'CRITICAL', 'Critical'


class RunbookInstance(TimeStampedModel):
    template = models.ForeignKey(RunbookTemplate, on_delete=models.PROTECT, related_name='instances')
    source_object_type = models.CharField(max_length=80)
    source_object_id = models.CharField(max_length=80)
    status = models.CharField(max_length=20, choices=RunbookInstanceStatus.choices, default=RunbookInstanceStatus.OPEN)
    priority = models.CharField(max_length=12, choices=RunbookPriority.choices, default=RunbookPriority.MEDIUM)
    summary = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-updated_at', '-id']
        indexes = [
            models.Index(fields=['status', '-updated_at']),
            models.Index(fields=['source_object_type', 'source_object_id']),
            models.Index(fields=['priority', '-updated_at']),
        ]


class RunbookStepActionKind(models.TextChoices):
    MANUAL = 'manual', 'Manual'
    API_ACTION = 'api_action', 'API action'
    REVIEW = 'review', 'Review'
    CONFIRM = 'confirm', 'Confirm'


class RunbookStepStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    READY = 'READY', 'Ready'
    RUNNING = 'RUNNING', 'Running'
    DONE = 'DONE', 'Done'
    FAILED = 'FAILED', 'Failed'
    SKIPPED = 'SKIPPED', 'Skipped'


class RunbookStep(TimeStampedModel):
    runbook_instance = models.ForeignKey(RunbookInstance, on_delete=models.CASCADE, related_name='steps')
    step_order = models.PositiveIntegerField()
    step_type = models.CharField(max_length=80)
    title = models.CharField(max_length=160)
    instructions = models.TextField(blank=True)
    action_kind = models.CharField(max_length=20, choices=RunbookStepActionKind.choices, default=RunbookStepActionKind.MANUAL)
    status = models.CharField(max_length=12, choices=RunbookStepStatus.choices, default=RunbookStepStatus.PENDING)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['step_order', 'id']
        unique_together = [('runbook_instance', 'step_order')]


class RunbookActionStatus(models.TextChoices):
    STARTED = 'STARTED', 'Started'
    SUCCESS = 'SUCCESS', 'Success'
    FAILED = 'FAILED', 'Failed'
    SKIPPED = 'SKIPPED', 'Skipped'


class RunbookActionResult(TimeStampedModel):
    runbook_step = models.ForeignKey(RunbookStep, on_delete=models.CASCADE, related_name='action_results')
    action_name = models.CharField(max_length=120)
    action_status = models.CharField(max_length=12, choices=RunbookActionStatus.choices)
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)
    result_summary = models.CharField(max_length=255, blank=True)
    output_refs = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']

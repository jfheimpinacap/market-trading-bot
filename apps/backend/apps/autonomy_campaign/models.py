from django.db import models

from apps.common.models import TimeStampedModel


class AutonomyCampaignSourceType(models.TextChoices):
    ROADMAP_PLAN = 'roadmap_plan', 'Roadmap plan'
    SCENARIO_RUN = 'scenario_run', 'Scenario run'
    MANUAL_BUNDLE = 'manual_bundle', 'Manual bundle'


class AutonomyCampaignStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    READY = 'READY', 'Ready'
    RUNNING = 'RUNNING', 'Running'
    PAUSED = 'PAUSED', 'Paused'
    BLOCKED = 'BLOCKED', 'Blocked'
    COMPLETED = 'COMPLETED', 'Completed'
    ABORTED = 'ABORTED', 'Aborted'
    FAILED = 'FAILED', 'Failed'


class AutonomyCampaignStepStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    READY = 'READY', 'Ready'
    RUNNING = 'RUNNING', 'Running'
    WAITING_APPROVAL = 'WAITING_APPROVAL', 'Waiting approval'
    OBSERVING = 'OBSERVING', 'Observing'
    DONE = 'DONE', 'Done'
    FAILED = 'FAILED', 'Failed'
    SKIPPED = 'SKIPPED', 'Skipped'
    ABORTED = 'ABORTED', 'Aborted'


class AutonomyCampaignActionType(models.TextChoices):
    APPLY_TRANSITION = 'APPLY_TRANSITION', 'Apply domain stage transition'
    START_ROLLOUT = 'START_ROLLOUT', 'Start rollout observation'
    EVALUATE_ROLLOUT = 'EVALUATE_ROLLOUT', 'Evaluate rollout observation'


class AutonomyCampaignCheckpointType(models.TextChoices):
    APPROVAL_REQUIRED = 'APPROVAL_REQUIRED', 'Approval required'
    ROLLOUT_OBSERVATION = 'ROLLOUT_OBSERVATION', 'Rollout observation'
    DEPENDENCY_CONFLICT = 'DEPENDENCY_CONFLICT', 'Dependency conflict'
    INCIDENT_BLOCK = 'INCIDENT_BLOCK', 'Incident/degraded block'
    MANUAL_REVIEW_REQUIRED = 'MANUAL_REVIEW_REQUIRED', 'Manual review required'


class AutonomyCampaignCheckpointStatus(models.TextChoices):
    OPEN = 'OPEN', 'Open'
    SATISFIED = 'SATISFIED', 'Satisfied'
    REJECTED = 'REJECTED', 'Rejected'
    EXPIRED = 'EXPIRED', 'Expired'


class AutonomyCampaign(TimeStampedModel):
    source_type = models.CharField(max_length=24, choices=AutonomyCampaignSourceType.choices)
    source_object_id = models.CharField(max_length=80)
    title = models.CharField(max_length=255)
    summary = models.CharField(max_length=255)
    status = models.CharField(max_length=16, choices=AutonomyCampaignStatus.choices, default=AutonomyCampaignStatus.DRAFT)
    current_wave = models.PositiveIntegerField(default=1)
    total_steps = models.PositiveIntegerField(default=0)
    completed_steps = models.PositiveIntegerField(default=0)
    blocked_steps = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['status', '-created_at'])]


class AutonomyCampaignStep(TimeStampedModel):
    campaign = models.ForeignKey(AutonomyCampaign, on_delete=models.CASCADE, related_name='steps')
    step_order = models.PositiveIntegerField()
    wave = models.PositiveIntegerField(default=1)
    domain = models.ForeignKey('autonomy_manager.AutonomyDomain', null=True, blank=True, on_delete=models.SET_NULL, related_name='campaign_steps')
    action_type = models.CharField(max_length=32, choices=AutonomyCampaignActionType.choices)
    status = models.CharField(max_length=24, choices=AutonomyCampaignStepStatus.choices, default=AutonomyCampaignStepStatus.PENDING)
    rationale = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['campaign_id', 'step_order']
        unique_together = ('campaign', 'step_order')
        indexes = [models.Index(fields=['campaign', 'wave', 'status'])]


class AutonomyCampaignCheckpoint(TimeStampedModel):
    campaign = models.ForeignKey(AutonomyCampaign, on_delete=models.CASCADE, related_name='checkpoints')
    step = models.ForeignKey(AutonomyCampaignStep, on_delete=models.CASCADE, related_name='checkpoints')
    checkpoint_type = models.CharField(max_length=32, choices=AutonomyCampaignCheckpointType.choices)
    status = models.CharField(max_length=16, choices=AutonomyCampaignCheckpointStatus.choices, default=AutonomyCampaignCheckpointStatus.OPEN)
    summary = models.CharField(max_length=255)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['campaign', 'status'])]

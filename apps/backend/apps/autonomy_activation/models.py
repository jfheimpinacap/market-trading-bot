from django.db import models

from apps.common.models import TimeStampedModel


class CampaignActivationStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    DISPATCHING = 'DISPATCHING', 'Dispatching'
    STARTED = 'STARTED', 'Started'
    BLOCKED = 'BLOCKED', 'Blocked'
    FAILED = 'FAILED', 'Failed'
    CANCELLED = 'CANCELLED', 'Cancelled'
    EXPIRED = 'EXPIRED', 'Expired'


class CampaignActivationTriggerSource(models.TextChoices):
    MANUAL_UI = 'manual_ui', 'Manual UI'
    MANUAL_API = 'manual_api', 'Manual API'
    APPROVAL_RESUME = 'approval_resume', 'Approval resume'


class ActivationRecommendationType(models.TextChoices):
    DISPATCH_NOW = 'DISPATCH_NOW', 'Dispatch now'
    REVALIDATE_BEFORE_DISPATCH = 'REVALIDATE_BEFORE_DISPATCH', 'Revalidate before dispatch'
    HOLD_DISPATCH = 'HOLD_DISPATCH', 'Hold dispatch'
    BLOCK_DISPATCH = 'BLOCK_DISPATCH', 'Block dispatch'
    WAIT_FOR_WINDOW = 'WAIT_FOR_WINDOW', 'Wait for window'
    EXPIRE_AUTHORIZATION = 'EXPIRE_AUTHORIZATION', 'Expire authorization'
    REORDER_DISPATCH_PRIORITY = 'REORDER_DISPATCH_PRIORITY', 'Reorder dispatch priority'


class CampaignActivation(TimeStampedModel):
    campaign = models.ForeignKey('autonomy_campaign.AutonomyCampaign', on_delete=models.CASCADE, related_name='activations')
    launch_authorization = models.ForeignKey('autonomy_launch.LaunchAuthorization', null=True, blank=True, on_delete=models.SET_NULL, related_name='campaign_activations')
    activation_status = models.CharField(max_length=16, choices=CampaignActivationStatus.choices, default=CampaignActivationStatus.PENDING)
    trigger_source = models.CharField(max_length=20, choices=CampaignActivationTriggerSource.choices, default=CampaignActivationTriggerSource.MANUAL_API)
    dispatch_rationale = models.CharField(max_length=255, blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    blockers = models.JSONField(default=list, blank=True)
    started_campaign_state = models.CharField(max_length=24, blank=True)
    failure_message = models.CharField(max_length=255, blank=True)
    activated_by = models.CharField(max_length=120, blank=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['campaign', '-created_at']), models.Index(fields=['activation_status', '-created_at'])]


class ActivationRun(TimeStampedModel):
    candidate_count = models.PositiveIntegerField(default=0)
    ready_count = models.PositiveIntegerField(default=0)
    blocked_count = models.PositiveIntegerField(default=0)
    expired_count = models.PositiveIntegerField(default=0)
    dispatched_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    current_program_posture = models.CharField(max_length=20)
    active_window = models.ForeignKey('autonomy_scheduler.ChangeWindow', null=True, blank=True, on_delete=models.SET_NULL, related_name='activation_runs')
    recommendation_summary = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class ActivationRecommendation(TimeStampedModel):
    activation_run = models.ForeignKey('autonomy_activation.ActivationRun', null=True, blank=True, on_delete=models.SET_NULL, related_name='recommendations')
    recommendation_type = models.CharField(max_length=40, choices=ActivationRecommendationType.choices)
    target_campaign = models.ForeignKey('autonomy_campaign.AutonomyCampaign', null=True, blank=True, on_delete=models.SET_NULL, related_name='activation_recommendations')
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    blockers = models.JSONField(default=list, blank=True)
    impacted_domains = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['recommendation_type', '-created_at'])]

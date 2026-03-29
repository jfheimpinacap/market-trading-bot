from django.db import models

from apps.common.models import TimeStampedModel


class LaunchReadinessStatus(models.TextChoices):
    READY_TO_START = 'READY_TO_START', 'Ready to start'
    CAUTION = 'CAUTION', 'Caution'
    WAITING = 'WAITING', 'Waiting'
    BLOCKED = 'BLOCKED', 'Blocked'


class LaunchAuthorizationStatus(models.TextChoices):
    PENDING_REVIEW = 'PENDING_REVIEW', 'Pending review'
    AUTHORIZED = 'AUTHORIZED', 'Authorized'
    HOLD = 'HOLD', 'Hold'
    BLOCKED = 'BLOCKED', 'Blocked'
    EXPIRED = 'EXPIRED', 'Expired'


class LaunchAuthorizationType(models.TextChoices):
    NORMAL_START = 'normal_start', 'Normal start'
    APPROVAL_REQUIRED_START = 'approval_required_start', 'Approval required start'
    BLOCKED_START = 'blocked_start', 'Blocked start'


class LaunchRecommendationType(models.TextChoices):
    START_NOW = 'START_NOW', 'Start now'
    AUTHORIZE_START = 'AUTHORIZE_START', 'Authorize start'
    HOLD_START = 'HOLD_START', 'Hold start'
    WAIT_FOR_WINDOW = 'WAIT_FOR_WINDOW', 'Wait for window'
    REQUIRE_APPROVAL_TO_START = 'REQUIRE_APPROVAL_TO_START', 'Require approval to start'
    BLOCK_START = 'BLOCK_START', 'Block start'
    REORDER_START_PRIORITY = 'REORDER_START_PRIORITY', 'Reorder start priority'


class LaunchReadinessSnapshot(TimeStampedModel):
    campaign = models.ForeignKey('autonomy_campaign.AutonomyCampaign', on_delete=models.CASCADE, related_name='launch_readiness_snapshots')
    launch_run = models.ForeignKey('autonomy_launch.LaunchRun', null=True, blank=True, on_delete=models.SET_NULL, related_name='readiness_snapshots')
    admission_status = models.CharField(max_length=16)
    program_posture = models.CharField(max_length=20)
    active_window_status = models.CharField(max_length=12)
    unresolved_checkpoints_count = models.PositiveIntegerField(default=0)
    unresolved_approvals_count = models.PositiveIntegerField(default=0)
    dependency_blocked = models.BooleanField(default=False)
    domain_conflict = models.BooleanField(default=False)
    incident_impact = models.PositiveIntegerField(default=0)
    degraded_impact = models.PositiveIntegerField(default=0)
    rollout_observation_impact = models.PositiveIntegerField(default=0)
    readiness_score = models.PositiveIntegerField(default=0)
    readiness_status = models.CharField(max_length=24, choices=LaunchReadinessStatus.choices, default=LaunchReadinessStatus.WAITING)
    blockers = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['campaign', '-created_at']), models.Index(fields=['readiness_status', '-created_at'])]


class LaunchAuthorization(TimeStampedModel):
    campaign = models.ForeignKey('autonomy_campaign.AutonomyCampaign', on_delete=models.CASCADE, related_name='launch_authorizations')
    authorization_status = models.CharField(max_length=16, choices=LaunchAuthorizationStatus.choices, default=LaunchAuthorizationStatus.PENDING_REVIEW)
    authorization_type = models.CharField(max_length=32, choices=LaunchAuthorizationType.choices, default=LaunchAuthorizationType.NORMAL_START)
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    requires_approval = models.BooleanField(default=False)
    approved_request = models.ForeignKey('approval_center.ApprovalRequest', null=True, blank=True, on_delete=models.SET_NULL, related_name='launch_authorizations')
    authorized_by = models.CharField(max_length=120, blank=True)
    authorized_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['campaign', '-created_at']), models.Index(fields=['authorization_status', '-created_at'])]


class LaunchRun(TimeStampedModel):
    candidate_count = models.PositiveIntegerField(default=0)
    ready_count = models.PositiveIntegerField(default=0)
    waiting_count = models.PositiveIntegerField(default=0)
    blocked_count = models.PositiveIntegerField(default=0)
    approval_required_count = models.PositiveIntegerField(default=0)
    active_window = models.ForeignKey('autonomy_scheduler.ChangeWindow', null=True, blank=True, on_delete=models.SET_NULL, related_name='launch_runs')
    program_posture = models.CharField(max_length=20)
    recommendation_summary = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class LaunchRecommendation(TimeStampedModel):
    launch_run = models.ForeignKey('autonomy_launch.LaunchRun', null=True, blank=True, on_delete=models.SET_NULL, related_name='recommendations')
    recommendation_type = models.CharField(max_length=40, choices=LaunchRecommendationType.choices)
    target_campaign = models.ForeignKey('autonomy_campaign.AutonomyCampaign', null=True, blank=True, on_delete=models.SET_NULL, related_name='launch_recommendations')
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    blockers = models.JSONField(default=list, blank=True)
    impacted_domains = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['recommendation_type', '-created_at'])]

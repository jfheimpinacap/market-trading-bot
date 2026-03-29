from django.db import models

from apps.common.models import TimeStampedModel


class RecoveryResumeReadiness(models.TextChoices):
    READY = 'READY', 'Ready'
    CAUTION = 'CAUTION', 'Caution'
    NOT_READY = 'NOT_READY', 'Not ready'


class RecoveryStatus(models.TextChoices):
    READY_TO_RESUME = 'READY_TO_RESUME', 'Ready to resume'
    RECOVERY_IN_PROGRESS = 'RECOVERY_IN_PROGRESS', 'Recovery in progress'
    KEEP_PAUSED = 'KEEP_PAUSED', 'Keep paused'
    BLOCKED = 'BLOCKED', 'Blocked'
    REVIEW_ABORT = 'REVIEW_ABORT', 'Review abort'
    CLOSE_CANDIDATE = 'CLOSE_CANDIDATE', 'Close candidate'


class RecoveryRecommendationType(models.TextChoices):
    RESUME_CAMPAIGN = 'RESUME_CAMPAIGN', 'Resume campaign'
    KEEP_PAUSED = 'KEEP_PAUSED', 'Keep paused'
    REQUIRE_MORE_RECOVERY = 'REQUIRE_MORE_RECOVERY', 'Require more recovery'
    ESCALATE_TO_APPROVAL = 'ESCALATE_TO_APPROVAL', 'Escalate to approval'
    REVIEW_FOR_ABORT = 'REVIEW_FOR_ABORT', 'Review for abort'
    CLOSE_CAMPAIGN = 'CLOSE_CAMPAIGN', 'Close campaign'
    REORDER_RECOVERY_PRIORITY = 'REORDER_RECOVERY_PRIORITY', 'Reorder recovery priority'


class RecoverySnapshot(TimeStampedModel):
    campaign = models.ForeignKey('autonomy_campaign.AutonomyCampaign', on_delete=models.CASCADE, related_name='recovery_snapshots')
    base_campaign_status = models.CharField(max_length=24)
    last_progress_at = models.DateTimeField(null=True, blank=True)
    paused_duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    blocker_count = models.PositiveIntegerField(default=0)
    blocker_types = models.JSONField(default=dict, blank=True)
    approvals_pending = models.BooleanField(default=False)
    checkpoints_pending = models.BooleanField(default=False)
    incident_pressure_level = models.PositiveIntegerField(default=0)
    recovery_score = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    recovery_priority = models.PositiveIntegerField(default=0)
    resume_readiness = models.CharField(max_length=16, choices=RecoveryResumeReadiness.choices, default=RecoveryResumeReadiness.NOT_READY)
    recovery_status = models.CharField(max_length=24, choices=RecoveryStatus.choices, default=RecoveryStatus.KEEP_PAUSED)
    rationale = models.CharField(max_length=255)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['campaign', '-created_at']), models.Index(fields=['recovery_status', '-created_at'])]


class RecoveryRun(TimeStampedModel):
    candidate_count = models.PositiveIntegerField(default=0)
    ready_to_resume_count = models.PositiveIntegerField(default=0)
    keep_paused_count = models.PositiveIntegerField(default=0)
    blocked_count = models.PositiveIntegerField(default=0)
    review_abort_count = models.PositiveIntegerField(default=0)
    close_candidate_count = models.PositiveIntegerField(default=0)
    approval_required_count = models.PositiveIntegerField(default=0)
    recommendation_summary = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class RecoveryRecommendation(TimeStampedModel):
    recovery_run = models.ForeignKey(RecoveryRun, null=True, blank=True, on_delete=models.SET_NULL, related_name='recommendations')
    recommendation_type = models.CharField(max_length=40, choices=RecoveryRecommendationType.choices)
    target_campaign = models.ForeignKey('autonomy_campaign.AutonomyCampaign', null=True, blank=True, on_delete=models.SET_NULL, related_name='recovery_recommendations')
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    blockers = models.JSONField(default=list, blank=True)
    impacted_domains = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['recommendation_type', '-created_at'])]

from django.db import models

from apps.common.models import TimeStampedModel


class AdvisoryResolutionStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    ACKNOWLEDGED = 'ACKNOWLEDGED', 'Acknowledged'
    ADOPTED = 'ADOPTED', 'Adopted'
    DEFERRED = 'DEFERRED', 'Deferred'
    REJECTED = 'REJECTED', 'Rejected'
    BLOCKED = 'BLOCKED', 'Blocked'
    CLOSED = 'CLOSED', 'Closed'


class AdvisoryResolutionType(models.TextChoices):
    MEMORY_NOTE_ACKNOWLEDGED = 'MEMORY_NOTE_ACKNOWLEDGED', 'Memory note acknowledged'
    ROADMAP_NOTE_ACKNOWLEDGED = 'ROADMAP_NOTE_ACKNOWLEDGED', 'Roadmap note acknowledged'
    SCENARIO_NOTE_ACKNOWLEDGED = 'SCENARIO_NOTE_ACKNOWLEDGED', 'Scenario note acknowledged'
    PROGRAM_NOTE_ACKNOWLEDGED = 'PROGRAM_NOTE_ACKNOWLEDGED', 'Program note acknowledged'
    MANAGER_NOTE_ACKNOWLEDGED = 'MANAGER_NOTE_ACKNOWLEDGED', 'Manager note acknowledged'
    MANUAL_REVIEW_REQUIRED = 'MANUAL_REVIEW_REQUIRED', 'Manual review required'


class AdvisoryResolutionRecommendationType(models.TextChoices):
    ACKNOWLEDGE_ADVISORY = 'ACKNOWLEDGE_ADVISORY', 'Acknowledge advisory'
    MARK_ADOPTED = 'MARK_ADOPTED', 'Mark adopted'
    MARK_DEFERRED = 'MARK_DEFERRED', 'Mark deferred'
    MARK_REJECTED = 'MARK_REJECTED', 'Mark rejected'
    REQUIRE_MANUAL_REVIEW = 'REQUIRE_MANUAL_REVIEW', 'Require manual review'
    KEEP_PENDING = 'KEEP_PENDING', 'Keep pending'
    REORDER_ADVISORY_RESOLUTION_PRIORITY = 'REORDER_ADVISORY_RESOLUTION_PRIORITY', 'Reorder advisory resolution priority'


class AdvisoryResolution(TimeStampedModel):
    advisory_artifact = models.ForeignKey('autonomy_advisory.AdvisoryArtifact', on_delete=models.CASCADE, related_name='resolution_events')
    insight = models.ForeignKey('autonomy_insights.CampaignInsight', on_delete=models.PROTECT, related_name='advisory_resolutions')
    campaign = models.ForeignKey('autonomy_campaign.AutonomyCampaign', null=True, blank=True, on_delete=models.SET_NULL, related_name='advisory_resolutions')
    resolution_status = models.CharField(max_length=24, choices=AdvisoryResolutionStatus.choices, default=AdvisoryResolutionStatus.PENDING)
    resolution_type = models.CharField(max_length=40, choices=AdvisoryResolutionType.choices, default=AdvisoryResolutionType.MANUAL_REVIEW_REQUIRED)
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    blockers = models.JSONField(default=list, blank=True)
    resolved_by = models.CharField(max_length=120, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    linked_artifact = models.CharField(max_length=128, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-updated_at', '-id']
        indexes = [
            models.Index(fields=['advisory_artifact', '-updated_at']),
            models.Index(fields=['resolution_status', '-updated_at']),
        ]


class AdvisoryResolutionRun(TimeStampedModel):
    candidate_count = models.PositiveIntegerField(default=0)
    pending_count = models.PositiveIntegerField(default=0)
    acknowledged_count = models.PositiveIntegerField(default=0)
    adopted_count = models.PositiveIntegerField(default=0)
    deferred_count = models.PositiveIntegerField(default=0)
    rejected_count = models.PositiveIntegerField(default=0)
    blocked_count = models.PositiveIntegerField(default=0)
    closed_count = models.PositiveIntegerField(default=0)
    recommendation_summary = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class AdvisoryResolutionRecommendation(TimeStampedModel):
    resolution_run = models.ForeignKey(AdvisoryResolutionRun, null=True, blank=True, on_delete=models.SET_NULL, related_name='recommendations')
    advisory_artifact = models.ForeignKey(
        'autonomy_advisory.AdvisoryArtifact',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='resolution_recommendations',
    )
    insight = models.ForeignKey('autonomy_insights.CampaignInsight', null=True, blank=True, on_delete=models.SET_NULL, related_name='advisory_resolution_recommendations')
    recommendation_type = models.CharField(max_length=56, choices=AdvisoryResolutionRecommendationType.choices)
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    blockers = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['recommendation_type', '-created_at'])]

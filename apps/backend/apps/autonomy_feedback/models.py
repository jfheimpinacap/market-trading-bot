from django.db import models

from apps.common.models import TimeStampedModel


class ResolutionStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    IN_PROGRESS = 'IN_PROGRESS', 'In progress'
    COMPLETED = 'COMPLETED', 'Completed'
    BLOCKED = 'BLOCKED', 'Blocked'
    REJECTED = 'REJECTED', 'Rejected'
    CLOSED = 'CLOSED', 'Closed'


class DownstreamStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    IN_PROGRESS = 'IN_PROGRESS', 'In progress'
    COMPLETED = 'COMPLETED', 'Completed'
    BLOCKED = 'BLOCKED', 'Blocked'
    REJECTED = 'REJECTED', 'Rejected'
    UNKNOWN = 'UNKNOWN', 'Unknown'


class ResolutionType(models.TextChoices):
    MEMORY_RESOLVED = 'MEMORY_RESOLVED', 'Memory resolved'
    POSTMORTEM_RESOLVED = 'POSTMORTEM_RESOLVED', 'Postmortem resolved'
    ROADMAP_FEEDBACK_REVIEWED = 'ROADMAP_FEEDBACK_REVIEWED', 'Roadmap feedback reviewed'
    MANUAL_REVIEW_REQUIRED = 'MANUAL_REVIEW_REQUIRED', 'Manual review required'


class FeedbackRecommendationType(models.TextChoices):
    REVIEW_MEMORY_RESOLUTION = 'REVIEW_MEMORY_RESOLUTION', 'Review memory resolution'
    REVIEW_POSTMORTEM_RESOLUTION = 'REVIEW_POSTMORTEM_RESOLUTION', 'Review postmortem resolution'
    REVIEW_ROADMAP_FEEDBACK_STATUS = 'REVIEW_ROADMAP_FEEDBACK_STATUS', 'Review roadmap feedback status'
    MARK_FOLLOWUP_COMPLETED = 'MARK_FOLLOWUP_COMPLETED', 'Mark followup completed'
    REQUIRE_MANUAL_REVIEW = 'REQUIRE_MANUAL_REVIEW', 'Require manual review'
    KEEP_PENDING = 'KEEP_PENDING', 'Keep pending'
    REORDER_FEEDBACK_PRIORITY = 'REORDER_FEEDBACK_PRIORITY', 'Reorder feedback priority'


class FollowupResolution(TimeStampedModel):
    campaign = models.ForeignKey('autonomy_campaign.AutonomyCampaign', on_delete=models.CASCADE, related_name='followup_resolutions')
    followup = models.OneToOneField('autonomy_followup.CampaignFollowup', on_delete=models.CASCADE, related_name='feedback_resolution')
    resolution_status = models.CharField(max_length=24, choices=ResolutionStatus.choices, default=ResolutionStatus.PENDING)
    downstream_status = models.CharField(max_length=24, choices=DownstreamStatus.choices, default=DownstreamStatus.UNKNOWN)
    resolution_type = models.CharField(max_length=40, choices=ResolutionType.choices, default=ResolutionType.MANUAL_REVIEW_REQUIRED)
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    blockers = models.JSONField(default=list, blank=True)
    resolved_by = models.CharField(max_length=120, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    linked_memory_document = models.ForeignKey(
        'memory_retrieval.MemoryDocument', null=True, blank=True, on_delete=models.SET_NULL, related_name='feedback_resolutions'
    )
    linked_postmortem_request = models.ForeignKey(
        'approval_center.ApprovalRequest', null=True, blank=True, on_delete=models.SET_NULL, related_name='feedback_resolutions'
    )
    linked_feedback_artifact = models.CharField(max_length=120, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-updated_at', '-id']
        indexes = [
            models.Index(fields=['resolution_status', '-updated_at']),
            models.Index(fields=['downstream_status', '-updated_at']),
        ]


class FeedbackRun(TimeStampedModel):
    candidate_count = models.PositiveIntegerField(default=0)
    pending_count = models.PositiveIntegerField(default=0)
    in_progress_count = models.PositiveIntegerField(default=0)
    completed_count = models.PositiveIntegerField(default=0)
    blocked_count = models.PositiveIntegerField(default=0)
    rejected_count = models.PositiveIntegerField(default=0)
    closed_loop_count = models.PositiveIntegerField(default=0)
    recommendation_summary = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class FeedbackRecommendation(TimeStampedModel):
    feedback_run = models.ForeignKey(FeedbackRun, null=True, blank=True, on_delete=models.SET_NULL, related_name='recommendations')
    target_campaign = models.ForeignKey('autonomy_campaign.AutonomyCampaign', null=True, blank=True, on_delete=models.SET_NULL, related_name='feedback_recommendations')
    followup = models.ForeignKey('autonomy_followup.CampaignFollowup', null=True, blank=True, on_delete=models.SET_NULL, related_name='feedback_recommendations')
    recommendation_type = models.CharField(max_length=48, choices=FeedbackRecommendationType.choices)
    followup_type = models.CharField(max_length=40, blank=True)
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    blockers = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['recommendation_type', '-created_at'])]

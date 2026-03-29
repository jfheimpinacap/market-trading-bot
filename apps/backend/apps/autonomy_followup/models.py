from django.db import models

from apps.common.models import TimeStampedModel


class FollowupType(models.TextChoices):
    MEMORY_INDEX = 'MEMORY_INDEX', 'Memory index'
    POSTMORTEM_REQUEST = 'POSTMORTEM_REQUEST', 'Postmortem request'
    ROADMAP_FEEDBACK = 'ROADMAP_FEEDBACK', 'Roadmap feedback'


class FollowupStatus(models.TextChoices):
    PENDING_REVIEW = 'PENDING_REVIEW', 'Pending review'
    READY = 'READY', 'Ready'
    EMITTED = 'EMITTED', 'Emitted'
    BLOCKED = 'BLOCKED', 'Blocked'
    DUPLICATE_SKIPPED = 'DUPLICATE_SKIPPED', 'Duplicate skipped'
    FAILED = 'FAILED', 'Failed'


class FollowupRecommendationType(models.TextChoices):
    EMIT_MEMORY_INDEX = 'EMIT_MEMORY_INDEX', 'Emit memory index'
    EMIT_POSTMORTEM_REQUEST = 'EMIT_POSTMORTEM_REQUEST', 'Emit postmortem request'
    EMIT_ROADMAP_FEEDBACK = 'EMIT_ROADMAP_FEEDBACK', 'Emit roadmap feedback'
    SKIP_DUPLICATE_FOLLOWUP = 'SKIP_DUPLICATE_FOLLOWUP', 'Skip duplicate followup'
    REQUIRE_MANUAL_REVIEW = 'REQUIRE_MANUAL_REVIEW', 'Require manual review'
    KEEP_PENDING = 'KEEP_PENDING', 'Keep pending'
    REORDER_FOLLOWUP_PRIORITY = 'REORDER_FOLLOWUP_PRIORITY', 'Reorder followup priority'


class CampaignFollowup(TimeStampedModel):
    campaign = models.ForeignKey('autonomy_campaign.AutonomyCampaign', on_delete=models.CASCADE, related_name='followups')
    closeout_report = models.ForeignKey('autonomy_closeout.CampaignCloseoutReport', on_delete=models.CASCADE, related_name='followups')
    followup_type = models.CharField(max_length=40, choices=FollowupType.choices)
    followup_status = models.CharField(max_length=24, choices=FollowupStatus.choices, default=FollowupStatus.PENDING_REVIEW)
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    blockers = models.JSONField(default=list, blank=True)
    emitted_by = models.CharField(max_length=120, blank=True)
    emitted_at = models.DateTimeField(null=True, blank=True)
    linked_memory_document = models.ForeignKey(
        'memory_retrieval.MemoryDocument', null=True, blank=True, on_delete=models.SET_NULL, related_name='autonomy_followups'
    )
    linked_postmortem_request = models.ForeignKey(
        'approval_center.ApprovalRequest', null=True, blank=True, on_delete=models.SET_NULL, related_name='autonomy_followups'
    )
    linked_feedback_artifact = models.CharField(max_length=120, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-updated_at', '-id']
        indexes = [models.Index(fields=['followup_status', '-updated_at']), models.Index(fields=['followup_type', '-updated_at'])]


class FollowupRun(TimeStampedModel):
    candidate_count = models.PositiveIntegerField(default=0)
    ready_count = models.PositiveIntegerField(default=0)
    blocked_count = models.PositiveIntegerField(default=0)
    emitted_count = models.PositiveIntegerField(default=0)
    duplicate_skipped_count = models.PositiveIntegerField(default=0)
    memory_followup_count = models.PositiveIntegerField(default=0)
    postmortem_followup_count = models.PositiveIntegerField(default=0)
    roadmap_feedback_count = models.PositiveIntegerField(default=0)
    recommendation_summary = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class FollowupRecommendation(TimeStampedModel):
    followup_run = models.ForeignKey(FollowupRun, null=True, blank=True, on_delete=models.SET_NULL, related_name='recommendations')
    target_campaign = models.ForeignKey('autonomy_campaign.AutonomyCampaign', null=True, blank=True, on_delete=models.SET_NULL, related_name='followup_recommendations')
    recommendation_type = models.CharField(max_length=48, choices=FollowupRecommendationType.choices)
    followup_type = models.CharField(max_length=40, choices=FollowupType.choices, blank=True)
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    blockers = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['recommendation_type', '-created_at'])]

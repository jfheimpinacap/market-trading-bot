from django.db import models

from apps.common.models import TimeStampedModel


class CampaignDispositionType(models.TextChoices):
    CLOSED = 'CLOSED', 'Closed'
    ABORTED = 'ABORTED', 'Aborted'
    RETIRED = 'RETIRED', 'Retired'
    COMPLETED_RECORDED = 'COMPLETED_RECORDED', 'Completed recorded'
    KEPT_OPEN = 'KEPT_OPEN', 'Kept open'


class CampaignDispositionStatus(models.TextChoices):
    PENDING_REVIEW = 'PENDING_REVIEW', 'Pending review'
    APPROVAL_REQUIRED = 'APPROVAL_REQUIRED', 'Approval required'
    READY = 'READY', 'Ready'
    APPLIED = 'APPLIED', 'Applied'
    BLOCKED = 'BLOCKED', 'Blocked'
    REJECTED = 'REJECTED', 'Rejected'
    EXPIRED = 'EXPIRED', 'Expired'


class DispositionReadiness(models.TextChoices):
    READY_TO_CLOSE = 'READY_TO_CLOSE', 'Ready to close'
    READY_TO_ABORT = 'READY_TO_ABORT', 'Ready to abort'
    READY_TO_RETIRE = 'READY_TO_RETIRE', 'Ready to retire'
    REQUIRE_MORE_REVIEW = 'REQUIRE_MORE_REVIEW', 'Require more review'
    KEEP_OPEN = 'KEEP_OPEN', 'Keep open'


class DispositionRecommendationType(models.TextChoices):
    CLOSE_CAMPAIGN = 'CLOSE_CAMPAIGN', 'Close campaign'
    ABORT_CAMPAIGN = 'ABORT_CAMPAIGN', 'Abort campaign'
    RETIRE_CAMPAIGN = 'RETIRE_CAMPAIGN', 'Retire campaign'
    RECORD_COMPLETION = 'RECORD_COMPLETION', 'Record completion'
    KEEP_CAMPAIGN_OPEN = 'KEEP_CAMPAIGN_OPEN', 'Keep campaign open'
    REQUIRE_APPROVAL_FOR_DISPOSITION = 'REQUIRE_APPROVAL_FOR_DISPOSITION', 'Require approval for disposition'
    REORDER_DISPOSITION_PRIORITY = 'REORDER_DISPOSITION_PRIORITY', 'Reorder disposition priority'


class CampaignDisposition(TimeStampedModel):
    campaign = models.ForeignKey('autonomy_campaign.AutonomyCampaign', on_delete=models.CASCADE, related_name='dispositions')
    disposition_type = models.CharField(max_length=32, choices=CampaignDispositionType.choices)
    disposition_status = models.CharField(max_length=24, choices=CampaignDispositionStatus.choices, default=CampaignDispositionStatus.PENDING_REVIEW)
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    blockers = models.JSONField(default=list, blank=True)
    requires_approval = models.BooleanField(default=False)
    linked_approval_request = models.ForeignKey('approval_center.ApprovalRequest', null=True, blank=True, on_delete=models.SET_NULL, related_name='autonomy_dispositions')
    applied_by = models.CharField(max_length=120, blank=True)
    applied_at = models.DateTimeField(null=True, blank=True)
    campaign_state_before = models.CharField(max_length=24, blank=True)
    campaign_state_after = models.CharField(max_length=24, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['campaign', '-created_at']), models.Index(fields=['disposition_status', '-created_at'])]


class DispositionRun(TimeStampedModel):
    candidate_count = models.PositiveIntegerField(default=0)
    ready_to_close_count = models.PositiveIntegerField(default=0)
    ready_to_abort_count = models.PositiveIntegerField(default=0)
    ready_to_retire_count = models.PositiveIntegerField(default=0)
    require_more_review_count = models.PositiveIntegerField(default=0)
    keep_open_count = models.PositiveIntegerField(default=0)
    approval_required_count = models.PositiveIntegerField(default=0)
    recommendation_summary = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class DispositionRecommendation(TimeStampedModel):
    disposition_run = models.ForeignKey(DispositionRun, null=True, blank=True, on_delete=models.SET_NULL, related_name='recommendations')
    recommendation_type = models.CharField(max_length=48, choices=DispositionRecommendationType.choices)
    target_campaign = models.ForeignKey('autonomy_campaign.AutonomyCampaign', null=True, blank=True, on_delete=models.SET_NULL, related_name='disposition_recommendations')
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    blockers = models.JSONField(default=list, blank=True)
    impacted_domains = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['recommendation_type', '-created_at'])]

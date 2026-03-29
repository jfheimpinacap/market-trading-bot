from django.db import models

from apps.common.models import TimeStampedModel


class CampaignCloseoutStatus(models.TextChoices):
    PENDING_REVIEW = 'PENDING_REVIEW', 'Pending review'
    READY = 'READY', 'Ready'
    APPROVAL_REQUIRED = 'APPROVAL_REQUIRED', 'Approval required'
    COMPLETED = 'COMPLETED', 'Completed'
    BLOCKED = 'BLOCKED', 'Blocked'


class CloseoutFindingType(models.TextChoices):
    SUCCESS_FACTOR = 'success_factor', 'Success factor'
    FAILURE_MODE = 'failure_mode', 'Failure mode'
    BLOCKER_PATTERN = 'blocker_pattern', 'Blocker pattern'
    APPROVAL_FRICTION = 'approval_friction', 'Approval friction'
    ROLLOUT_LESSON = 'rollout_lesson', 'Rollout lesson'
    INCIDENT_LESSON = 'incident_lesson', 'Incident lesson'
    RECOVERY_LESSON = 'recovery_lesson', 'Recovery lesson'
    DISPOSITION_LESSON = 'disposition_lesson', 'Disposition lesson'


class CloseoutRecommendationType(models.TextChoices):
    COMPLETE_CLOSEOUT = 'COMPLETE_CLOSEOUT', 'Complete closeout'
    SEND_TO_POSTMORTEM = 'SEND_TO_POSTMORTEM', 'Send to postmortem'
    INDEX_IN_MEMORY = 'INDEX_IN_MEMORY', 'Index in memory'
    PREPARE_ROADMAP_FEEDBACK = 'PREPARE_ROADMAP_FEEDBACK', 'Prepare roadmap feedback'
    REQUIRE_MANUAL_CLOSEOUT_REVIEW = 'REQUIRE_MANUAL_CLOSEOUT_REVIEW', 'Require manual closeout review'
    KEEP_OPEN_FOR_FOLLOWUP = 'KEEP_OPEN_FOR_FOLLOWUP', 'Keep open for follow up'
    REORDER_CLOSEOUT_PRIORITY = 'REORDER_CLOSEOUT_PRIORITY', 'Reorder closeout priority'


class CampaignCloseoutReport(TimeStampedModel):
    campaign = models.OneToOneField('autonomy_campaign.AutonomyCampaign', on_delete=models.CASCADE, related_name='closeout_report')
    disposition_type = models.CharField(max_length=32)
    closeout_status = models.CharField(max_length=24, choices=CampaignCloseoutStatus.choices, default=CampaignCloseoutStatus.PENDING_REVIEW)
    executive_summary = models.CharField(max_length=255)
    lifecycle_summary = models.JSONField(default=dict, blank=True)
    major_blockers = models.JSONField(default=list, blank=True)
    incident_summary = models.JSONField(default=dict, blank=True)
    intervention_summary = models.JSONField(default=dict, blank=True)
    recovery_summary = models.JSONField(default=dict, blank=True)
    final_outcome_summary = models.CharField(max_length=255)
    requires_postmortem = models.BooleanField(default=False)
    requires_memory_index = models.BooleanField(default=False)
    requires_roadmap_feedback = models.BooleanField(default=False)
    linked_postmortem_request = models.CharField(max_length=120, blank=True)
    linked_memory_document = models.ForeignKey('memory_retrieval.MemoryDocument', null=True, blank=True, on_delete=models.SET_NULL, related_name='autonomy_closeout_reports')
    linked_feedback_artifact = models.CharField(max_length=120, blank=True)
    closed_out_by = models.CharField(max_length=120, blank=True)
    closed_out_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-updated_at', '-id']
        indexes = [models.Index(fields=['closeout_status', '-updated_at'])]


class CloseoutFinding(TimeStampedModel):
    closeout_report = models.ForeignKey(CampaignCloseoutReport, on_delete=models.CASCADE, related_name='findings')
    finding_type = models.CharField(max_length=32, choices=CloseoutFindingType.choices)
    severity_or_weight = models.CharField(max_length=16, default='MEDIUM')
    summary = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    recommended_followup = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['finding_type', '-created_at'])]


class CloseoutRun(TimeStampedModel):
    candidate_count = models.PositiveIntegerField(default=0)
    ready_count = models.PositiveIntegerField(default=0)
    blocked_count = models.PositiveIntegerField(default=0)
    requires_postmortem_count = models.PositiveIntegerField(default=0)
    requires_memory_index_count = models.PositiveIntegerField(default=0)
    requires_roadmap_feedback_count = models.PositiveIntegerField(default=0)
    completed_closeout_count = models.PositiveIntegerField(default=0)
    recommendation_summary = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class CloseoutRecommendation(TimeStampedModel):
    closeout_run = models.ForeignKey(CloseoutRun, null=True, blank=True, on_delete=models.SET_NULL, related_name='recommendations')
    recommendation_type = models.CharField(max_length=48, choices=CloseoutRecommendationType.choices)
    target_campaign = models.ForeignKey('autonomy_campaign.AutonomyCampaign', null=True, blank=True, on_delete=models.SET_NULL, related_name='closeout_recommendations')
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    blockers = models.JSONField(default=list, blank=True)
    impacted_domains = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['recommendation_type', '-created_at'])]

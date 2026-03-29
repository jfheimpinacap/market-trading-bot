from django.db import models

from apps.common.models import TimeStampedModel


class InterventionSourceType(models.TextChoices):
    OPERATIONS_RECOMMENDATION = 'operations_recommendation', 'Operations recommendation'
    ATTENTION_SIGNAL = 'attention_signal', 'Attention signal'
    MANUAL = 'manual', 'Manual'
    INCIDENT_RESPONSE = 'incident_response', 'Incident response'


class InterventionRequestedAction(models.TextChoices):
    PAUSE_CAMPAIGN = 'PAUSE_CAMPAIGN', 'Pause campaign'
    RESUME_CAMPAIGN = 'RESUME_CAMPAIGN', 'Resume campaign'
    ESCALATE_TO_APPROVAL = 'ESCALATE_TO_APPROVAL', 'Escalate to approval'
    REVIEW_FOR_ABORT = 'REVIEW_FOR_ABORT', 'Review for abort'
    CLEAR_TO_CONTINUE = 'CLEAR_TO_CONTINUE', 'Clear to continue'


class InterventionRequestStatus(models.TextChoices):
    OPEN = 'OPEN', 'Open'
    APPROVAL_REQUIRED = 'APPROVAL_REQUIRED', 'Approval required'
    READY = 'READY', 'Ready'
    EXECUTED = 'EXECUTED', 'Executed'
    REJECTED = 'REJECTED', 'Rejected'
    BLOCKED = 'BLOCKED', 'Blocked'
    EXPIRED = 'EXPIRED', 'Expired'


class InterventionActionType(models.TextChoices):
    PAUSE = 'pause', 'Pause'
    RESUME = 'resume', 'Resume'
    ESCALATE = 'escalate', 'Escalate'
    ABORT_REVIEW = 'abort_review', 'Abort review'
    CONTINUE_CLEARANCE = 'continue_clearance', 'Continue clearance'


class InterventionActionStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    EXECUTING = 'EXECUTING', 'Executing'
    EXECUTED = 'EXECUTED', 'Executed'
    BLOCKED = 'BLOCKED', 'Blocked'
    FAILED = 'FAILED', 'Failed'
    CANCELLED = 'CANCELLED', 'Cancelled'


class InterventionOutcomeType(models.TextChoices):
    CAMPAIGN_PAUSED = 'CAMPAIGN_PAUSED', 'Campaign paused'
    CAMPAIGN_RESUMED = 'CAMPAIGN_RESUMED', 'Campaign resumed'
    APPROVAL_OPENED = 'APPROVAL_OPENED', 'Approval opened'
    ABORT_REVIEW_OPENED = 'ABORT_REVIEW_OPENED', 'Abort review opened'
    CONTINUE_CONFIRMED = 'CONTINUE_CONFIRMED', 'Continue confirmed'
    NO_STATE_CHANGE = 'NO_STATE_CHANGE', 'No state change'
    ACTION_BLOCKED = 'ACTION_BLOCKED', 'Action blocked'
    ACTION_FAILED = 'ACTION_FAILED', 'Action failed'


class CampaignInterventionRequest(TimeStampedModel):
    campaign = models.ForeignKey('autonomy_campaign.AutonomyCampaign', on_delete=models.CASCADE, related_name='intervention_requests')
    source_type = models.CharField(max_length=32, choices=InterventionSourceType.choices)
    requested_action = models.CharField(max_length=32, choices=InterventionRequestedAction.choices)
    request_status = models.CharField(max_length=20, choices=InterventionRequestStatus.choices, default=InterventionRequestStatus.OPEN)
    severity = models.CharField(max_length=12, default='MEDIUM')
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    blockers = models.JSONField(default=list, blank=True)
    linked_signal = models.ForeignKey('autonomy_operations.CampaignAttentionSignal', null=True, blank=True, on_delete=models.SET_NULL, related_name='intervention_requests')
    linked_recommendation = models.ForeignKey('autonomy_operations.OperationsRecommendation', null=True, blank=True, on_delete=models.SET_NULL, related_name='intervention_requests')
    approval_request = models.ForeignKey('approval_center.ApprovalRequest', null=True, blank=True, on_delete=models.SET_NULL, related_name='intervention_requests')
    requested_by = models.CharField(max_length=120, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['request_status', '-created_at']),
            models.Index(fields=['campaign', '-created_at']),
            models.Index(fields=['requested_action', '-created_at']),
        ]


class CampaignInterventionAction(TimeStampedModel):
    campaign = models.ForeignKey('autonomy_campaign.AutonomyCampaign', on_delete=models.CASCADE, related_name='intervention_actions')
    intervention_request = models.ForeignKey(CampaignInterventionRequest, null=True, blank=True, on_delete=models.SET_NULL, related_name='actions')
    action_type = models.CharField(max_length=24, choices=InterventionActionType.choices)
    action_status = models.CharField(max_length=16, choices=InterventionActionStatus.choices, default=InterventionActionStatus.PENDING)
    executed_by = models.CharField(max_length=120, blank=True)
    executed_at = models.DateTimeField(null=True, blank=True)
    failure_message = models.CharField(max_length=255, blank=True)
    result_summary = models.CharField(max_length=255, blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    blockers = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['action_status', '-created_at']), models.Index(fields=['campaign', '-created_at'])]


class InterventionRun(TimeStampedModel):
    active_campaign_count = models.PositiveIntegerField(default=0)
    open_request_count = models.PositiveIntegerField(default=0)
    approval_required_count = models.PositiveIntegerField(default=0)
    ready_request_count = models.PositiveIntegerField(default=0)
    blocked_request_count = models.PositiveIntegerField(default=0)
    executed_recent_count = models.PositiveIntegerField(default=0)
    recommendation_summary = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class InterventionOutcome(TimeStampedModel):
    action = models.ForeignKey(CampaignInterventionAction, on_delete=models.CASCADE, related_name='outcomes')
    outcome_type = models.CharField(max_length=32, choices=InterventionOutcomeType.choices)
    campaign_state_before = models.CharField(max_length=24, blank=True)
    campaign_state_after = models.CharField(max_length=24, blank=True)
    summary = models.CharField(max_length=255)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['outcome_type', '-created_at'])]

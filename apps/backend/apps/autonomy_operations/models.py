from django.db import models

from apps.common.models import TimeStampedModel


class CampaignRuntimeStatus(models.TextChoices):
    ON_TRACK = 'ON_TRACK', 'On track'
    CAUTION = 'CAUTION', 'Caution'
    STALLED = 'STALLED', 'Stalled'
    BLOCKED = 'BLOCKED', 'Blocked'
    WAITING_APPROVAL = 'WAITING_APPROVAL', 'Waiting approval'
    OBSERVING = 'OBSERVING', 'Observing'


class CampaignAttentionSeverity(models.TextChoices):
    LOW = 'LOW', 'Low'
    MEDIUM = 'MEDIUM', 'Medium'
    HIGH = 'HIGH', 'High'
    CRITICAL = 'CRITICAL', 'Critical'


class CampaignAttentionSignalType(models.TextChoices):
    STALLED_PROGRESS = 'stalled_progress', 'Stalled progress'
    BLOCKED_CHECKPOINT = 'blocked_checkpoint', 'Blocked checkpoint'
    APPROVAL_DELAY = 'approval_delay', 'Approval delay'
    ROLLOUT_WARNING = 'rollout_warning', 'Rollout warning'
    INCIDENT_IMPACT = 'incident_impact', 'Incident impact'
    DEGRADED_PRESSURE = 'degraded_pressure', 'Degraded pressure'
    DOMAIN_CONFLICT = 'domain_conflict', 'Domain conflict'
    OBSERVATION_TIMEOUT = 'observation_timeout', 'Observation timeout'


class CampaignAttentionSignalStatus(models.TextChoices):
    OPEN = 'OPEN', 'Open'
    ACKNOWLEDGED = 'ACKNOWLEDGED', 'Acknowledged'
    RESOLVED = 'RESOLVED', 'Resolved'


class OperationsRecommendationType(models.TextChoices):
    CONTINUE_CAMPAIGN = 'CONTINUE_CAMPAIGN', 'Continue campaign'
    PAUSE_CAMPAIGN = 'PAUSE_CAMPAIGN', 'Pause campaign'
    RESUME_CAMPAIGN = 'RESUME_CAMPAIGN', 'Resume campaign'
    ESCALATE_TO_APPROVAL = 'ESCALATE_TO_APPROVAL', 'Escalate to approval'
    REVIEW_FOR_ABORT = 'REVIEW_FOR_ABORT', 'Review for abort'
    WAIT_FOR_CHECKPOINT = 'WAIT_FOR_CHECKPOINT', 'Wait for checkpoint'
    CLEAR_TO_CONTINUE = 'CLEAR_TO_CONTINUE', 'Clear to continue'
    REORDER_OPERATOR_ATTENTION = 'REORDER_OPERATOR_ATTENTION', 'Reorder operator attention'


class CampaignRuntimeSnapshot(TimeStampedModel):
    campaign = models.ForeignKey('autonomy_campaign.AutonomyCampaign', on_delete=models.CASCADE, related_name='operations_runtime_snapshots')
    campaign_status = models.CharField(max_length=16)
    current_wave = models.PositiveIntegerField(null=True, blank=True)
    current_step = models.ForeignKey('autonomy_campaign.AutonomyCampaignStep', null=True, blank=True, on_delete=models.SET_NULL, related_name='operations_runtime_snapshots')
    current_checkpoint = models.ForeignKey('autonomy_campaign.AutonomyCampaignCheckpoint', null=True, blank=True, on_delete=models.SET_NULL, related_name='operations_runtime_snapshots')
    started_at = models.DateTimeField(null=True, blank=True)
    last_progress_at = models.DateTimeField(null=True, blank=True)
    stalled_duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    open_checkpoints_count = models.PositiveIntegerField(default=0)
    pending_approvals_count = models.PositiveIntegerField(default=0)
    blocked_steps_count = models.PositiveIntegerField(default=0)
    incident_impact = models.PositiveIntegerField(default=0)
    degraded_impact = models.PositiveIntegerField(default=0)
    rollout_observation_impact = models.PositiveIntegerField(default=0)
    progress_score = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    runtime_status = models.CharField(max_length=20, choices=CampaignRuntimeStatus.choices, default=CampaignRuntimeStatus.ON_TRACK)
    blockers = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['campaign', '-created_at']), models.Index(fields=['runtime_status', '-created_at'])]


class CampaignAttentionSignal(TimeStampedModel):
    campaign = models.ForeignKey('autonomy_campaign.AutonomyCampaign', on_delete=models.CASCADE, related_name='operations_attention_signals')
    severity = models.CharField(max_length=12, choices=CampaignAttentionSeverity.choices)
    signal_type = models.CharField(max_length=32, choices=CampaignAttentionSignalType.choices)
    status = models.CharField(max_length=16, choices=CampaignAttentionSignalStatus.choices, default=CampaignAttentionSignalStatus.OPEN)
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    blockers = models.JSONField(default=list, blank=True)
    linked_trace = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['status', '-created_at']), models.Index(fields=['severity', '-created_at'])]


class OperationsRun(TimeStampedModel):
    active_campaign_count = models.PositiveIntegerField(default=0)
    on_track_count = models.PositiveIntegerField(default=0)
    caution_count = models.PositiveIntegerField(default=0)
    stalled_count = models.PositiveIntegerField(default=0)
    blocked_count = models.PositiveIntegerField(default=0)
    waiting_approval_count = models.PositiveIntegerField(default=0)
    observing_count = models.PositiveIntegerField(default=0)
    attention_signal_count = models.PositiveIntegerField(default=0)
    recommendation_summary = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class OperationsRecommendation(TimeStampedModel):
    operations_run = models.ForeignKey('autonomy_operations.OperationsRun', null=True, blank=True, on_delete=models.SET_NULL, related_name='recommendations')
    recommendation_type = models.CharField(max_length=40, choices=OperationsRecommendationType.choices)
    target_campaign = models.ForeignKey('autonomy_campaign.AutonomyCampaign', null=True, blank=True, on_delete=models.SET_NULL, related_name='operations_recommendations')
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    blockers = models.JSONField(default=list, blank=True)
    impacted_domains = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['recommendation_type', '-created_at'])]

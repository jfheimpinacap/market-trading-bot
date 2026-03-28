from django.db import models

from apps.common.models import TimeStampedModel


class ProgramConcurrencyPosture(models.TextChoices):
    NORMAL = 'NORMAL', 'Normal'
    CONSTRAINED = 'CONSTRAINED', 'Constrained'
    HIGH_RISK = 'HIGH_RISK', 'High risk'
    FROZEN = 'FROZEN', 'Frozen'


class CampaignConcurrencyRuleType(models.TextChoices):
    MAX_ACTIVE_CAMPAIGNS = 'max_active_campaigns', 'Max active campaigns'
    INCOMPATIBLE_DOMAINS = 'incompatible_domains', 'Incompatible domains'
    BLOCK_IF_DEGRADED = 'block_if_degraded', 'Block if degraded'
    BLOCK_IF_UNDER_OBSERVATION = 'block_if_under_observation', 'Block if under observation'
    BLOCK_IF_CRITICAL_INCIDENT = 'block_if_critical_incident', 'Block if critical incident'


class CampaignHealthStatus(models.TextChoices):
    HEALTHY = 'HEALTHY', 'Healthy'
    CAUTION = 'CAUTION', 'Caution'
    BLOCKED = 'BLOCKED', 'Blocked'
    AT_RISK = 'AT_RISK', 'At risk'


class ProgramRecommendationType(models.TextChoices):
    CONTINUE_CAMPAIGN = 'CONTINUE_CAMPAIGN', 'Continue campaign'
    PAUSE_CAMPAIGN = 'PAUSE_CAMPAIGN', 'Pause campaign'
    REORDER_QUEUE = 'REORDER_QUEUE', 'Reorder queue'
    ABORT_CAMPAIGN = 'ABORT_CAMPAIGN', 'Abort campaign'
    HOLD_NEW_CAMPAIGNS = 'HOLD_NEW_CAMPAIGNS', 'Hold new campaigns'
    SAFE_TO_START_NEXT = 'SAFE_TO_START_NEXT', 'Safe to start next'
    WAIT_FOR_STABILIZATION = 'WAIT_FOR_STABILIZATION', 'Wait for stabilization'


class AutonomyProgramState(TimeStampedModel):
    active_campaigns_count = models.PositiveIntegerField(default=0)
    blocked_campaigns_count = models.PositiveIntegerField(default=0)
    waiting_approval_count = models.PositiveIntegerField(default=0)
    observing_campaigns_count = models.PositiveIntegerField(default=0)
    degraded_domains_count = models.PositiveIntegerField(default=0)
    locked_domains = models.JSONField(default=list, blank=True)
    concurrency_posture = models.CharField(max_length=20, choices=ProgramConcurrencyPosture.choices, default=ProgramConcurrencyPosture.NORMAL)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class CampaignConcurrencyRule(TimeStampedModel):
    rule_type = models.CharField(max_length=40, choices=CampaignConcurrencyRuleType.choices)
    scope = models.CharField(max_length=80, default='global')
    config = models.JSONField(default=dict, blank=True)
    rationale = models.CharField(max_length=255)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['created_at', 'id']
        indexes = [models.Index(fields=['rule_type', 'scope'])]


class CampaignHealthSnapshot(TimeStampedModel):
    campaign = models.ForeignKey('autonomy_campaign.AutonomyCampaign', on_delete=models.CASCADE, related_name='program_health_snapshots')
    active_wave = models.PositiveIntegerField(default=1)
    domain_count = models.PositiveIntegerField(default=0)
    blocked_checkpoints = models.PositiveIntegerField(default=0)
    open_approvals = models.PositiveIntegerField(default=0)
    rollout_warnings = models.PositiveIntegerField(default=0)
    incident_impact = models.PositiveIntegerField(default=0)
    degraded_impact = models.PositiveIntegerField(default=0)
    health_score = models.PositiveIntegerField(default=100)
    health_status = models.CharField(max_length=16, choices=CampaignHealthStatus.choices, default=CampaignHealthStatus.HEALTHY)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['campaign', '-created_at']), models.Index(fields=['health_status', '-created_at'])]


class ProgramRecommendation(TimeStampedModel):
    recommendation_type = models.CharField(max_length=32, choices=ProgramRecommendationType.choices)
    target_campaign = models.ForeignKey('autonomy_campaign.AutonomyCampaign', null=True, blank=True, on_delete=models.SET_NULL, related_name='program_recommendations')
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    impacted_domains = models.JSONField(default=list, blank=True)
    blockers = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['recommendation_type', '-created_at'])]

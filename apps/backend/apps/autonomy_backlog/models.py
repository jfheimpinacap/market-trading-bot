from django.db import models

from apps.common.models import TimeStampedModel


class GovernanceBacklogType(models.TextChoices):
    ROADMAP_CHANGE_CANDIDATE = 'ROADMAP_CHANGE_CANDIDATE', 'Roadmap change candidate'
    SCENARIO_CAUTION_CANDIDATE = 'SCENARIO_CAUTION_CANDIDATE', 'Scenario caution candidate'
    PROGRAM_GOVERNANCE_CANDIDATE = 'PROGRAM_GOVERNANCE_CANDIDATE', 'Program governance candidate'
    MANAGER_REVIEW_ITEM = 'MANAGER_REVIEW_ITEM', 'Manager review item'
    OPERATOR_REVIEW_ITEM = 'OPERATOR_REVIEW_ITEM', 'Operator review item'


class GovernanceBacklogStatus(models.TextChoices):
    PENDING_REVIEW = 'PENDING_REVIEW', 'Pending review'
    READY = 'READY', 'Ready'
    PRIORITIZED = 'PRIORITIZED', 'Prioritized'
    DEFERRED = 'DEFERRED', 'Deferred'
    BLOCKED = 'BLOCKED', 'Blocked'
    CLOSED = 'CLOSED', 'Closed'


class GovernanceBacklogPriority(models.TextChoices):
    LOW = 'LOW', 'Low'
    MEDIUM = 'MEDIUM', 'Medium'
    HIGH = 'HIGH', 'High'
    CRITICAL = 'CRITICAL', 'Critical'


class BacklogRecommendationType(models.TextChoices):
    CREATE_BACKLOG_ITEM = 'CREATE_BACKLOG_ITEM', 'Create backlog item'
    PRIORITIZE_BACKLOG_ITEM = 'PRIORITIZE_BACKLOG_ITEM', 'Prioritize backlog item'
    DEFER_BACKLOG_ITEM = 'DEFER_BACKLOG_ITEM', 'Defer backlog item'
    SKIP_DUPLICATE_BACKLOG = 'SKIP_DUPLICATE_BACKLOG', 'Skip duplicate backlog item'
    REQUIRE_MANUAL_BACKLOG_REVIEW = 'REQUIRE_MANUAL_BACKLOG_REVIEW', 'Require manual backlog review'
    REORDER_BACKLOG_PRIORITY = 'REORDER_BACKLOG_PRIORITY', 'Reorder backlog priority'


class GovernanceBacklogItem(TimeStampedModel):
    advisory_artifact = models.ForeignKey('autonomy_advisory.AdvisoryArtifact', on_delete=models.CASCADE, related_name='backlog_items')
    advisory_resolution = models.ForeignKey('autonomy_advisory_resolution.AdvisoryResolution', on_delete=models.PROTECT, related_name='backlog_items')
    insight = models.ForeignKey('autonomy_insights.CampaignInsight', on_delete=models.PROTECT, related_name='governance_backlog_items')
    campaign = models.ForeignKey('autonomy_campaign.AutonomyCampaign', null=True, blank=True, on_delete=models.SET_NULL, related_name='governance_backlog_items')
    backlog_type = models.CharField(max_length=40, choices=GovernanceBacklogType.choices)
    backlog_status = models.CharField(max_length=24, choices=GovernanceBacklogStatus.choices, default=GovernanceBacklogStatus.PENDING_REVIEW)
    priority_level = models.CharField(max_length=16, choices=GovernanceBacklogPriority.choices, default=GovernanceBacklogPriority.MEDIUM)
    target_scope = models.CharField(max_length=24)
    summary = models.CharField(max_length=255)
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    blockers = models.JSONField(default=list, blank=True)
    created_by = models.CharField(max_length=120, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-updated_at', '-id']
        indexes = [
            models.Index(fields=['advisory_artifact', '-updated_at']),
            models.Index(fields=['backlog_status', '-updated_at']),
            models.Index(fields=['priority_level', '-updated_at']),
        ]


class BacklogRun(TimeStampedModel):
    candidate_count = models.PositiveIntegerField(default=0)
    ready_count = models.PositiveIntegerField(default=0)
    blocked_count = models.PositiveIntegerField(default=0)
    created_count = models.PositiveIntegerField(default=0)
    duplicate_skipped_count = models.PositiveIntegerField(default=0)
    prioritized_count = models.PositiveIntegerField(default=0)
    recommendation_summary = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class BacklogRecommendation(TimeStampedModel):
    backlog_run = models.ForeignKey(BacklogRun, null=True, blank=True, on_delete=models.SET_NULL, related_name='recommendations')
    advisory_artifact = models.ForeignKey('autonomy_advisory.AdvisoryArtifact', null=True, blank=True, on_delete=models.SET_NULL, related_name='backlog_recommendations')
    insight = models.ForeignKey('autonomy_insights.CampaignInsight', null=True, blank=True, on_delete=models.SET_NULL, related_name='backlog_recommendations')
    backlog_item = models.ForeignKey(GovernanceBacklogItem, null=True, blank=True, on_delete=models.SET_NULL, related_name='recommendations')
    recommendation_type = models.CharField(max_length=48, choices=BacklogRecommendationType.choices)
    backlog_type = models.CharField(max_length=40, choices=GovernanceBacklogType.choices, blank=True)
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    blockers = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['recommendation_type', '-created_at'])]

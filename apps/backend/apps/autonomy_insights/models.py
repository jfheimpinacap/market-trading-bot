from django.db import models

from apps.common.models import TimeStampedModel


class InsightType(models.TextChoices):
    SUCCESS_PATTERN = 'success_pattern', 'Success pattern'
    FAILURE_PATTERN = 'failure_pattern', 'Failure pattern'
    BLOCKER_PATTERN = 'blocker_pattern', 'Blocker pattern'
    APPROVAL_PATTERN = 'approval_pattern', 'Approval pattern'
    INCIDENT_PATTERN = 'incident_pattern', 'Incident pattern'
    RECOVERY_PATTERN = 'recovery_pattern', 'Recovery pattern'
    ROLLOUT_PATTERN = 'rollout_pattern', 'Rollout pattern'
    GOVERNANCE_PATTERN = 'governance_pattern', 'Governance pattern'


class InsightScope(models.TextChoices):
    CAMPAIGN = 'campaign', 'Campaign'
    DOMAIN = 'domain', 'Domain'
    CROSS_CAMPAIGN = 'cross_campaign', 'Cross campaign'


class RecommendationTarget(models.TextChoices):
    MEMORY = 'memory', 'Memory'
    ROADMAP = 'roadmap', 'Roadmap'
    SCENARIO = 'scenario', 'Scenario'
    PROGRAM = 'program', 'Program'
    MANAGER = 'manager', 'Manager'
    OPERATOR_REVIEW = 'operator_review', 'Operator review'


class InsightRecommendationType(models.TextChoices):
    REGISTER_MEMORY_PRECEDENT = 'REGISTER_MEMORY_PRECEDENT', 'Register memory precedent'
    PREPARE_ROADMAP_GOVERNANCE_NOTE = 'PREPARE_ROADMAP_GOVERNANCE_NOTE', 'Prepare roadmap governance note'
    PREPARE_SCENARIO_CAUTION = 'PREPARE_SCENARIO_CAUTION', 'Prepare scenario caution'
    PREPARE_PROGRAM_POLICY_NOTE = 'PREPARE_PROGRAM_POLICY_NOTE', 'Prepare program policy note'
    REQUIRE_OPERATOR_REVIEW = 'REQUIRE_OPERATOR_REVIEW', 'Require operator review'
    REORDER_INSIGHT_PRIORITY = 'REORDER_INSIGHT_PRIORITY', 'Reorder insight priority'


class CampaignInsight(TimeStampedModel):
    campaign = models.ForeignKey('autonomy_campaign.AutonomyCampaign', null=True, blank=True, on_delete=models.SET_NULL, related_name='insights')
    insight_type = models.CharField(max_length=32, choices=InsightType.choices)
    scope = models.CharField(max_length=24, choices=InsightScope.choices, default=InsightScope.CAMPAIGN)
    summary = models.CharField(max_length=255)
    evidence_summary = models.JSONField(default=dict, blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    recommended_followup = models.CharField(max_length=255, blank=True)
    recommendation_target = models.CharField(max_length=24, choices=RecommendationTarget.choices)
    confidence = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    reviewed = models.BooleanField(default=False)
    reviewed_by = models.CharField(max_length=120, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['insight_type', '-created_at']), models.Index(fields=['reviewed', '-created_at'])]


class InsightRun(TimeStampedModel):
    candidate_count = models.PositiveIntegerField(default=0)
    lifecycle_closed_count = models.PositiveIntegerField(default=0)
    insight_count = models.PositiveIntegerField(default=0)
    success_pattern_count = models.PositiveIntegerField(default=0)
    failure_pattern_count = models.PositiveIntegerField(default=0)
    blocker_pattern_count = models.PositiveIntegerField(default=0)
    governance_pattern_count = models.PositiveIntegerField(default=0)
    recommendation_summary = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class InsightRecommendation(TimeStampedModel):
    insight_run = models.ForeignKey(InsightRun, null=True, blank=True, on_delete=models.SET_NULL, related_name='recommendations')
    target_campaign = models.ForeignKey('autonomy_campaign.AutonomyCampaign', null=True, blank=True, on_delete=models.SET_NULL, related_name='insight_recommendations')
    campaign_insight = models.ForeignKey(CampaignInsight, null=True, blank=True, on_delete=models.SET_NULL, related_name='recommendations')
    recommendation_type = models.CharField(max_length=48, choices=InsightRecommendationType.choices)
    insight_type = models.CharField(max_length=32, choices=InsightType.choices)
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    blockers = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['recommendation_type', '-created_at'])]

from django.db import models

from apps.common.models import TimeStampedModel


class GovernanceDecisionType(models.TextChoices):
    ROADMAP_DECISION_PACKAGE = 'ROADMAP_DECISION_PACKAGE', 'Roadmap decision package'
    SCENARIO_DECISION_PACKAGE = 'SCENARIO_DECISION_PACKAGE', 'Scenario decision package'
    PROGRAM_DECISION_PACKAGE = 'PROGRAM_DECISION_PACKAGE', 'Program decision package'
    MANAGER_DECISION_NOTE = 'MANAGER_DECISION_NOTE', 'Manager decision note'
    OPERATOR_DECISION_NOTE = 'OPERATOR_DECISION_NOTE', 'Operator decision note'


class GovernanceDecisionStatus(models.TextChoices):
    PENDING_REVIEW = 'PENDING_REVIEW', 'Pending review'
    READY = 'READY', 'Ready'
    REGISTERED = 'REGISTERED', 'Registered'
    BLOCKED = 'BLOCKED', 'Blocked'
    DUPLICATE_SKIPPED = 'DUPLICATE_SKIPPED', 'Duplicate skipped'
    ACKNOWLEDGED = 'ACKNOWLEDGED', 'Acknowledged'


class GovernanceDecisionTargetScope(models.TextChoices):
    ROADMAP = 'roadmap', 'Roadmap'
    SCENARIO = 'scenario', 'Scenario'
    PROGRAM = 'program', 'Program'
    MANAGER = 'manager', 'Manager'
    OPERATOR_REVIEW = 'operator_review', 'Operator review'


class DecisionRecommendationType(models.TextChoices):
    REGISTER_ROADMAP_DECISION = 'REGISTER_ROADMAP_DECISION', 'Register roadmap decision'
    REGISTER_SCENARIO_DECISION = 'REGISTER_SCENARIO_DECISION', 'Register scenario decision'
    REGISTER_PROGRAM_DECISION = 'REGISTER_PROGRAM_DECISION', 'Register program decision'
    REGISTER_MANAGER_DECISION = 'REGISTER_MANAGER_DECISION', 'Register manager decision'
    SKIP_DUPLICATE_DECISION = 'SKIP_DUPLICATE_DECISION', 'Skip duplicate decision'
    REQUIRE_MANUAL_DECISION_REVIEW = 'REQUIRE_MANUAL_DECISION_REVIEW', 'Require manual decision review'
    REORDER_DECISION_PRIORITY = 'REORDER_DECISION_PRIORITY', 'Reorder decision priority'


class GovernanceDecision(TimeStampedModel):
    planning_proposal = models.ForeignKey('autonomy_intake.PlanningProposal', on_delete=models.CASCADE, related_name='governance_decisions')
    planning_resolution = models.ForeignKey('autonomy_planning_review.PlanningProposalResolution', on_delete=models.CASCADE, related_name='governance_decisions')
    backlog_item = models.ForeignKey('autonomy_backlog.GovernanceBacklogItem', null=True, blank=True, on_delete=models.SET_NULL, related_name='governance_decisions')
    advisory_artifact = models.ForeignKey('autonomy_advisory.AdvisoryArtifact', null=True, blank=True, on_delete=models.SET_NULL, related_name='governance_decisions')
    insight = models.ForeignKey('autonomy_insights.CampaignInsight', null=True, blank=True, on_delete=models.SET_NULL, related_name='governance_decisions')
    campaign = models.ForeignKey('autonomy_campaign.AutonomyCampaign', null=True, blank=True, on_delete=models.SET_NULL, related_name='governance_decisions')
    decision_type = models.CharField(max_length=40, choices=GovernanceDecisionType.choices)
    decision_status = models.CharField(max_length=24, choices=GovernanceDecisionStatus.choices, default=GovernanceDecisionStatus.PENDING_REVIEW)
    target_scope = models.CharField(max_length=24, choices=GovernanceDecisionTargetScope.choices)
    priority_level = models.CharField(max_length=16, choices=[('LOW', 'Low'), ('MEDIUM', 'Medium'), ('HIGH', 'High'), ('CRITICAL', 'Critical')], default='MEDIUM')
    summary = models.CharField(max_length=255)
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    blockers = models.JSONField(default=list, blank=True)
    registered_by = models.CharField(max_length=120, blank=True)
    registered_at = models.DateTimeField(null=True, blank=True)
    linked_target_artifact = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-updated_at', '-id']
        indexes = [
            models.Index(fields=['planning_proposal', 'target_scope', '-updated_at']),
            models.Index(fields=['decision_status', '-updated_at']),
            models.Index(fields=['target_scope', 'priority_level', '-updated_at']),
        ]


class DecisionRun(TimeStampedModel):
    candidate_count = models.PositiveIntegerField(default=0)
    ready_count = models.PositiveIntegerField(default=0)
    blocked_count = models.PositiveIntegerField(default=0)
    registered_count = models.PositiveIntegerField(default=0)
    duplicate_skipped_count = models.PositiveIntegerField(default=0)
    roadmap_decision_count = models.PositiveIntegerField(default=0)
    scenario_decision_count = models.PositiveIntegerField(default=0)
    program_decision_count = models.PositiveIntegerField(default=0)
    manager_decision_count = models.PositiveIntegerField(default=0)
    recommendation_summary = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class DecisionRecommendation(TimeStampedModel):
    decision_run = models.ForeignKey(DecisionRun, null=True, blank=True, on_delete=models.SET_NULL, related_name='recommendations')
    planning_proposal = models.ForeignKey('autonomy_intake.PlanningProposal', null=True, blank=True, on_delete=models.SET_NULL, related_name='decision_recommendations')
    governance_decision = models.ForeignKey(GovernanceDecision, null=True, blank=True, on_delete=models.SET_NULL, related_name='recommendations')
    decision_type = models.CharField(max_length=40, choices=GovernanceDecisionType.choices, blank=True)
    recommendation_type = models.CharField(max_length=48, choices=DecisionRecommendationType.choices)
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    blockers = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['recommendation_type', '-created_at'])]

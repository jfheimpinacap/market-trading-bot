from django.db import models

from apps.common.models import TimeStampedModel


class PlanningProposalType(models.TextChoices):
    ROADMAP_PROPOSAL = 'ROADMAP_PROPOSAL', 'Roadmap proposal'
    SCENARIO_PROPOSAL = 'SCENARIO_PROPOSAL', 'Scenario proposal'
    PROGRAM_REVIEW_PROPOSAL = 'PROGRAM_REVIEW_PROPOSAL', 'Program review proposal'
    MANAGER_REVIEW_PROPOSAL = 'MANAGER_REVIEW_PROPOSAL', 'Manager review proposal'
    OPERATOR_REVIEW_PROPOSAL = 'OPERATOR_REVIEW_PROPOSAL', 'Operator review proposal'


class PlanningProposalStatus(models.TextChoices):
    PENDING_REVIEW = 'PENDING_REVIEW', 'Pending review'
    READY = 'READY', 'Ready'
    EMITTED = 'EMITTED', 'Emitted'
    BLOCKED = 'BLOCKED', 'Blocked'
    DUPLICATE_SKIPPED = 'DUPLICATE_SKIPPED', 'Duplicate skipped'
    ACKNOWLEDGED = 'ACKNOWLEDGED', 'Acknowledged'


class PlanningTargetScope(models.TextChoices):
    ROADMAP = 'roadmap', 'Roadmap'
    SCENARIO = 'scenario', 'Scenario'
    PROGRAM = 'program', 'Program'
    MANAGER = 'manager', 'Manager'
    OPERATOR_REVIEW = 'operator_review', 'Operator review'


class IntakeRecommendationType(models.TextChoices):
    EMIT_ROADMAP_PROPOSAL = 'EMIT_ROADMAP_PROPOSAL', 'Emit roadmap proposal'
    EMIT_SCENARIO_PROPOSAL = 'EMIT_SCENARIO_PROPOSAL', 'Emit scenario proposal'
    EMIT_PROGRAM_REVIEW_PROPOSAL = 'EMIT_PROGRAM_REVIEW_PROPOSAL', 'Emit program review proposal'
    EMIT_MANAGER_REVIEW_PROPOSAL = 'EMIT_MANAGER_REVIEW_PROPOSAL', 'Emit manager review proposal'
    EMIT_OPERATOR_REVIEW_PROPOSAL = 'EMIT_OPERATOR_REVIEW_PROPOSAL', 'Emit operator review proposal'
    SKIP_DUPLICATE_PROPOSAL = 'SKIP_DUPLICATE_PROPOSAL', 'Skip duplicate proposal'
    REQUIRE_MANUAL_INTAKE_REVIEW = 'REQUIRE_MANUAL_INTAKE_REVIEW', 'Require manual intake review'
    REORDER_INTAKE_PRIORITY = 'REORDER_INTAKE_PRIORITY', 'Reorder intake priority'


class PlanningProposal(TimeStampedModel):
    backlog_item = models.ForeignKey('autonomy_backlog.GovernanceBacklogItem', on_delete=models.CASCADE, related_name='planning_proposals')
    advisory_artifact = models.ForeignKey('autonomy_advisory.AdvisoryArtifact', null=True, blank=True, on_delete=models.SET_NULL, related_name='planning_proposals')
    insight = models.ForeignKey('autonomy_insights.CampaignInsight', null=True, blank=True, on_delete=models.SET_NULL, related_name='planning_proposals')
    campaign = models.ForeignKey('autonomy_campaign.AutonomyCampaign', null=True, blank=True, on_delete=models.SET_NULL, related_name='planning_proposals')
    proposal_type = models.CharField(max_length=40, choices=PlanningProposalType.choices)
    proposal_status = models.CharField(max_length=24, choices=PlanningProposalStatus.choices, default=PlanningProposalStatus.PENDING_REVIEW)
    target_scope = models.CharField(max_length=24, choices=PlanningTargetScope.choices)
    priority_level = models.CharField(max_length=16, choices=[('LOW', 'Low'), ('MEDIUM', 'Medium'), ('HIGH', 'High'), ('CRITICAL', 'Critical')], default='MEDIUM')
    summary = models.CharField(max_length=255)
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    blockers = models.JSONField(default=list, blank=True)
    emitted_by = models.CharField(max_length=120, blank=True)
    emitted_at = models.DateTimeField(null=True, blank=True)
    linked_target_artifact = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-updated_at', '-id']
        indexes = [
            models.Index(fields=['backlog_item', 'target_scope', '-updated_at']),
            models.Index(fields=['proposal_status', '-updated_at']),
            models.Index(fields=['priority_level', '-updated_at']),
        ]


class IntakeRun(TimeStampedModel):
    candidate_count = models.PositiveIntegerField(default=0)
    ready_count = models.PositiveIntegerField(default=0)
    blocked_count = models.PositiveIntegerField(default=0)
    emitted_count = models.PositiveIntegerField(default=0)
    duplicate_skipped_count = models.PositiveIntegerField(default=0)
    roadmap_proposal_count = models.PositiveIntegerField(default=0)
    scenario_proposal_count = models.PositiveIntegerField(default=0)
    program_proposal_count = models.PositiveIntegerField(default=0)
    manager_proposal_count = models.PositiveIntegerField(default=0)
    recommendation_summary = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class IntakeRecommendation(TimeStampedModel):
    intake_run = models.ForeignKey(IntakeRun, null=True, blank=True, on_delete=models.SET_NULL, related_name='recommendations')
    backlog_item = models.ForeignKey('autonomy_backlog.GovernanceBacklogItem', null=True, blank=True, on_delete=models.SET_NULL, related_name='intake_recommendations')
    proposal = models.ForeignKey(PlanningProposal, null=True, blank=True, on_delete=models.SET_NULL, related_name='intake_recommendations')
    proposal_type = models.CharField(max_length=40, choices=PlanningProposalType.choices, blank=True)
    recommendation_type = models.CharField(max_length=48, choices=IntakeRecommendationType.choices)
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    blockers = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['recommendation_type', '-created_at'])]

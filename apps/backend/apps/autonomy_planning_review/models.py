from django.db import models

from apps.common.models import TimeStampedModel


class PlanningProposalResolutionStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    ACKNOWLEDGED = 'ACKNOWLEDGED', 'Acknowledged'
    ACCEPTED = 'ACCEPTED', 'Accepted'
    DEFERRED = 'DEFERRED', 'Deferred'
    REJECTED = 'REJECTED', 'Rejected'
    BLOCKED = 'BLOCKED', 'Blocked'
    CLOSED = 'CLOSED', 'Closed'


class PlanningProposalResolutionType(models.TextChoices):
    ROADMAP_PROPOSAL_ACKNOWLEDGED = 'ROADMAP_PROPOSAL_ACKNOWLEDGED', 'Roadmap proposal acknowledged'
    SCENARIO_PROPOSAL_ACKNOWLEDGED = 'SCENARIO_PROPOSAL_ACKNOWLEDGED', 'Scenario proposal acknowledged'
    PROGRAM_REVIEW_ACKNOWLEDGED = 'PROGRAM_REVIEW_ACKNOWLEDGED', 'Program review acknowledged'
    MANAGER_REVIEW_ACKNOWLEDGED = 'MANAGER_REVIEW_ACKNOWLEDGED', 'Manager review acknowledged'
    OPERATOR_REVIEW_ACKNOWLEDGED = 'OPERATOR_REVIEW_ACKNOWLEDGED', 'Operator review acknowledged'
    MANUAL_REVIEW_REQUIRED = 'MANUAL_REVIEW_REQUIRED', 'Manual review required'


class PlanningReviewRecommendationType(models.TextChoices):
    ACKNOWLEDGE_PROPOSAL = 'ACKNOWLEDGE_PROPOSAL', 'Acknowledge proposal'
    MARK_ACCEPTED = 'MARK_ACCEPTED', 'Mark accepted'
    MARK_DEFERRED = 'MARK_DEFERRED', 'Mark deferred'
    MARK_REJECTED = 'MARK_REJECTED', 'Mark rejected'
    REQUIRE_MANUAL_REVIEW = 'REQUIRE_MANUAL_REVIEW', 'Require manual review'
    KEEP_PENDING = 'KEEP_PENDING', 'Keep pending'
    REORDER_PLANNING_REVIEW_PRIORITY = 'REORDER_PLANNING_REVIEW_PRIORITY', 'Reorder planning review priority'


class PlanningProposalResolution(TimeStampedModel):
    planning_proposal = models.OneToOneField('autonomy_intake.PlanningProposal', on_delete=models.CASCADE, related_name='planning_resolution')
    backlog_item = models.ForeignKey('autonomy_backlog.GovernanceBacklogItem', null=True, blank=True, on_delete=models.SET_NULL, related_name='planning_resolutions')
    advisory_artifact = models.ForeignKey('autonomy_advisory.AdvisoryArtifact', null=True, blank=True, on_delete=models.SET_NULL, related_name='planning_resolutions')
    insight = models.ForeignKey('autonomy_insights.CampaignInsight', null=True, blank=True, on_delete=models.SET_NULL, related_name='planning_resolutions')
    campaign = models.ForeignKey('autonomy_campaign.AutonomyCampaign', null=True, blank=True, on_delete=models.SET_NULL, related_name='planning_resolutions')
    resolution_status = models.CharField(max_length=24, choices=PlanningProposalResolutionStatus.choices, default=PlanningProposalResolutionStatus.PENDING)
    resolution_type = models.CharField(max_length=40, choices=PlanningProposalResolutionType.choices, default=PlanningProposalResolutionType.MANUAL_REVIEW_REQUIRED)
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    blockers = models.JSONField(default=list, blank=True)
    resolved_by = models.CharField(max_length=120, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    linked_target_artifact = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-updated_at', '-id']
        indexes = [
            models.Index(fields=['planning_proposal', '-updated_at']),
            models.Index(fields=['resolution_status', '-updated_at']),
        ]


class PlanningReviewRun(TimeStampedModel):
    candidate_count = models.PositiveIntegerField(default=0)
    pending_count = models.PositiveIntegerField(default=0)
    acknowledged_count = models.PositiveIntegerField(default=0)
    accepted_count = models.PositiveIntegerField(default=0)
    deferred_count = models.PositiveIntegerField(default=0)
    rejected_count = models.PositiveIntegerField(default=0)
    blocked_count = models.PositiveIntegerField(default=0)
    closed_count = models.PositiveIntegerField(default=0)
    recommendation_summary = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class PlanningReviewRecommendation(TimeStampedModel):
    review_run = models.ForeignKey(PlanningReviewRun, null=True, blank=True, on_delete=models.SET_NULL, related_name='recommendations')
    planning_proposal = models.ForeignKey('autonomy_intake.PlanningProposal', null=True, blank=True, on_delete=models.SET_NULL, related_name='planning_review_recommendations')
    backlog_item = models.ForeignKey('autonomy_backlog.GovernanceBacklogItem', null=True, blank=True, on_delete=models.SET_NULL, related_name='planning_review_recommendations')
    recommendation_type = models.CharField(max_length=56, choices=PlanningReviewRecommendationType.choices)
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    blockers = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['recommendation_type', '-created_at'])]

from django.db import models

from apps.common.models import TimeStampedModel


class SeedResolutionStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    ACKNOWLEDGED = 'ACKNOWLEDGED', 'Acknowledged'
    ACCEPTED = 'ACCEPTED', 'Accepted'
    DEFERRED = 'DEFERRED', 'Deferred'
    REJECTED = 'REJECTED', 'Rejected'
    BLOCKED = 'BLOCKED', 'Blocked'
    CLOSED = 'CLOSED', 'Closed'


class SeedResolutionType(models.TextChoices):
    ROADMAP_SEED_ACKNOWLEDGED = 'ROADMAP_SEED_ACKNOWLEDGED', 'Roadmap seed acknowledged'
    SCENARIO_SEED_ACKNOWLEDGED = 'SCENARIO_SEED_ACKNOWLEDGED', 'Scenario seed acknowledged'
    PROGRAM_SEED_ACKNOWLEDGED = 'PROGRAM_SEED_ACKNOWLEDGED', 'Program seed acknowledged'
    MANAGER_SEED_ACKNOWLEDGED = 'MANAGER_SEED_ACKNOWLEDGED', 'Manager seed acknowledged'
    OPERATOR_SEED_ACKNOWLEDGED = 'OPERATOR_SEED_ACKNOWLEDGED', 'Operator seed acknowledged'
    MANUAL_REVIEW_REQUIRED = 'MANUAL_REVIEW_REQUIRED', 'Manual review required'


class SeedReviewRecommendationType(models.TextChoices):
    ACKNOWLEDGE_SEED = 'ACKNOWLEDGE_SEED', 'Acknowledge seed'
    MARK_SEED_ACCEPTED = 'MARK_SEED_ACCEPTED', 'Mark seed accepted'
    MARK_SEED_DEFERRED = 'MARK_SEED_DEFERRED', 'Mark seed deferred'
    MARK_SEED_REJECTED = 'MARK_SEED_REJECTED', 'Mark seed rejected'
    REQUIRE_MANUAL_SEED_REVIEW = 'REQUIRE_MANUAL_SEED_REVIEW', 'Require manual seed review'
    KEEP_SEED_PENDING = 'KEEP_SEED_PENDING', 'Keep seed pending'
    REORDER_SEED_REVIEW_PRIORITY = 'REORDER_SEED_REVIEW_PRIORITY', 'Reorder seed review priority'


class SeedResolution(TimeStampedModel):
    governance_seed = models.OneToOneField('autonomy_seed.GovernanceSeed', on_delete=models.CASCADE, related_name='seed_resolution')
    resolution_status = models.CharField(max_length=24, choices=SeedResolutionStatus.choices, default=SeedResolutionStatus.PENDING)
    resolution_type = models.CharField(max_length=48, choices=SeedResolutionType.choices, default=SeedResolutionType.MANUAL_REVIEW_REQUIRED)
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
            models.Index(fields=['resolution_status', '-updated_at']),
            models.Index(fields=['governance_seed', '-updated_at']),
        ]


class SeedReviewRun(TimeStampedModel):
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


class SeedReviewRecommendation(TimeStampedModel):
    review_run = models.ForeignKey(SeedReviewRun, null=True, blank=True, on_delete=models.SET_NULL, related_name='recommendations')
    governance_seed = models.ForeignKey('autonomy_seed.GovernanceSeed', null=True, blank=True, on_delete=models.SET_NULL, related_name='seed_review_recommendations')
    recommendation_type = models.CharField(max_length=56, choices=SeedReviewRecommendationType.choices)
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    blockers = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['recommendation_type', '-created_at'])]

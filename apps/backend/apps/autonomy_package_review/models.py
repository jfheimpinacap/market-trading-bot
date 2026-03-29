from django.db import models

from apps.common.models import TimeStampedModel


class PackageResolutionStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    ACKNOWLEDGED = 'ACKNOWLEDGED', 'Acknowledged'
    ADOPTED = 'ADOPTED', 'Adopted'
    DEFERRED = 'DEFERRED', 'Deferred'
    REJECTED = 'REJECTED', 'Rejected'
    BLOCKED = 'BLOCKED', 'Blocked'
    CLOSED = 'CLOSED', 'Closed'


class PackageResolutionType(models.TextChoices):
    ROADMAP_PACKAGE_ACKNOWLEDGED = 'ROADMAP_PACKAGE_ACKNOWLEDGED', 'Roadmap package acknowledged'
    SCENARIO_PACKAGE_ACKNOWLEDGED = 'SCENARIO_PACKAGE_ACKNOWLEDGED', 'Scenario package acknowledged'
    PROGRAM_PACKAGE_ACKNOWLEDGED = 'PROGRAM_PACKAGE_ACKNOWLEDGED', 'Program package acknowledged'
    MANAGER_PACKAGE_ACKNOWLEDGED = 'MANAGER_PACKAGE_ACKNOWLEDGED', 'Manager package acknowledged'
    OPERATOR_PACKAGE_ACKNOWLEDGED = 'OPERATOR_PACKAGE_ACKNOWLEDGED', 'Operator package acknowledged'
    MANUAL_REVIEW_REQUIRED = 'MANUAL_REVIEW_REQUIRED', 'Manual review required'


class PackageReviewRecommendationType(models.TextChoices):
    ACKNOWLEDGE_PACKAGE = 'ACKNOWLEDGE_PACKAGE', 'Acknowledge package'
    MARK_PACKAGE_ADOPTED = 'MARK_PACKAGE_ADOPTED', 'Mark package adopted'
    MARK_PACKAGE_DEFERRED = 'MARK_PACKAGE_DEFERRED', 'Mark package deferred'
    MARK_PACKAGE_REJECTED = 'MARK_PACKAGE_REJECTED', 'Mark package rejected'
    REQUIRE_MANUAL_PACKAGE_REVIEW = 'REQUIRE_MANUAL_PACKAGE_REVIEW', 'Require manual package review'
    KEEP_PACKAGE_PENDING = 'KEEP_PACKAGE_PENDING', 'Keep package pending'
    REORDER_PACKAGE_REVIEW_PRIORITY = 'REORDER_PACKAGE_REVIEW_PRIORITY', 'Reorder package review priority'


class PackageResolution(TimeStampedModel):
    governance_package = models.OneToOneField('autonomy_package.GovernancePackage', on_delete=models.CASCADE, related_name='package_resolution')
    resolution_status = models.CharField(max_length=24, choices=PackageResolutionStatus.choices, default=PackageResolutionStatus.PENDING)
    resolution_type = models.CharField(max_length=48, choices=PackageResolutionType.choices, default=PackageResolutionType.MANUAL_REVIEW_REQUIRED)
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
            models.Index(fields=['governance_package', '-updated_at']),
            models.Index(fields=['resolution_status', '-updated_at']),
        ]


class PackageReviewRun(TimeStampedModel):
    candidate_count = models.PositiveIntegerField(default=0)
    pending_count = models.PositiveIntegerField(default=0)
    acknowledged_count = models.PositiveIntegerField(default=0)
    adopted_count = models.PositiveIntegerField(default=0)
    deferred_count = models.PositiveIntegerField(default=0)
    rejected_count = models.PositiveIntegerField(default=0)
    blocked_count = models.PositiveIntegerField(default=0)
    closed_count = models.PositiveIntegerField(default=0)
    recommendation_summary = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class PackageReviewRecommendation(TimeStampedModel):
    review_run = models.ForeignKey(PackageReviewRun, null=True, blank=True, on_delete=models.SET_NULL, related_name='recommendations')
    governance_package = models.ForeignKey('autonomy_package.GovernancePackage', null=True, blank=True, on_delete=models.SET_NULL, related_name='package_review_recommendations')
    recommendation_type = models.CharField(max_length=56, choices=PackageReviewRecommendationType.choices)
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    blockers = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['recommendation_type', '-created_at'])]

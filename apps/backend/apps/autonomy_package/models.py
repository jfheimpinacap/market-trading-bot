from django.db import models

from apps.common.models import TimeStampedModel


class GovernancePackageType(models.TextChoices):
    ROADMAP_CHANGE_PACKAGE = 'ROADMAP_CHANGE_PACKAGE', 'Roadmap change package'
    SCENARIO_CAUTION_PACKAGE = 'SCENARIO_CAUTION_PACKAGE', 'Scenario caution package'
    PROGRAM_GOVERNANCE_PACKAGE = 'PROGRAM_GOVERNANCE_PACKAGE', 'Program governance package'
    MANAGER_REVIEW_PACKAGE = 'MANAGER_REVIEW_PACKAGE', 'Manager review package'
    OPERATOR_REVIEW_PACKAGE = 'OPERATOR_REVIEW_PACKAGE', 'Operator review package'


class GovernancePackageStatus(models.TextChoices):
    PENDING_REVIEW = 'PENDING_REVIEW', 'Pending review'
    READY = 'READY', 'Ready'
    REGISTERED = 'REGISTERED', 'Registered'
    BLOCKED = 'BLOCKED', 'Blocked'
    DUPLICATE_SKIPPED = 'DUPLICATE_SKIPPED', 'Duplicate skipped'
    ACKNOWLEDGED = 'ACKNOWLEDGED', 'Acknowledged'


class GovernancePackageTargetScope(models.TextChoices):
    ROADMAP = 'roadmap', 'Roadmap'
    SCENARIO = 'scenario', 'Scenario'
    PROGRAM = 'program', 'Program'
    MANAGER = 'manager', 'Manager'
    OPERATOR_REVIEW = 'operator_review', 'Operator review'


class PackageRecommendationType(models.TextChoices):
    REGISTER_ROADMAP_PACKAGE = 'REGISTER_ROADMAP_PACKAGE', 'Register roadmap package'
    REGISTER_SCENARIO_PACKAGE = 'REGISTER_SCENARIO_PACKAGE', 'Register scenario package'
    REGISTER_PROGRAM_PACKAGE = 'REGISTER_PROGRAM_PACKAGE', 'Register program package'
    REGISTER_MANAGER_PACKAGE = 'REGISTER_MANAGER_PACKAGE', 'Register manager package'
    SKIP_DUPLICATE_PACKAGE = 'SKIP_DUPLICATE_PACKAGE', 'Skip duplicate package'
    REQUIRE_MANUAL_PACKAGE_REVIEW = 'REQUIRE_MANUAL_PACKAGE_REVIEW', 'Require manual package review'
    REORDER_PACKAGE_PRIORITY = 'REORDER_PACKAGE_PRIORITY', 'Reorder package priority'


class GovernancePackage(TimeStampedModel):
    package_type = models.CharField(max_length=40, choices=GovernancePackageType.choices)
    package_status = models.CharField(max_length=24, choices=GovernancePackageStatus.choices, default=GovernancePackageStatus.PENDING_REVIEW)
    target_scope = models.CharField(max_length=24, choices=GovernancePackageTargetScope.choices)
    priority_level = models.CharField(max_length=16, choices=[('LOW', 'Low'), ('MEDIUM', 'Medium'), ('HIGH', 'High'), ('CRITICAL', 'Critical')], default='MEDIUM')
    title = models.CharField(max_length=255)
    summary = models.CharField(max_length=255)
    rationale = models.CharField(max_length=255)
    decision_count = models.PositiveIntegerField(default=0)
    linked_decisions = models.ManyToManyField('autonomy_decision.GovernanceDecision', related_name='governance_packages', blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    blockers = models.JSONField(default=list, blank=True)
    grouping_key = models.CharField(max_length=120)
    registered_by = models.CharField(max_length=120, blank=True)
    registered_at = models.DateTimeField(null=True, blank=True)
    linked_target_artifact = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-updated_at', '-id']
        indexes = [
            models.Index(fields=['grouping_key', 'target_scope', '-updated_at']),
            models.Index(fields=['package_status', '-updated_at']),
            models.Index(fields=['target_scope', 'priority_level', '-updated_at']),
        ]


class PackageRun(TimeStampedModel):
    candidate_count = models.PositiveIntegerField(default=0)
    ready_count = models.PositiveIntegerField(default=0)
    blocked_count = models.PositiveIntegerField(default=0)
    registered_count = models.PositiveIntegerField(default=0)
    duplicate_skipped_count = models.PositiveIntegerField(default=0)
    roadmap_package_count = models.PositiveIntegerField(default=0)
    scenario_package_count = models.PositiveIntegerField(default=0)
    program_package_count = models.PositiveIntegerField(default=0)
    manager_package_count = models.PositiveIntegerField(default=0)
    recommendation_summary = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class PackageRecommendation(TimeStampedModel):
    package_run = models.ForeignKey(PackageRun, null=True, blank=True, on_delete=models.SET_NULL, related_name='recommendations')
    governance_decision = models.ForeignKey('autonomy_decision.GovernanceDecision', null=True, blank=True, on_delete=models.SET_NULL, related_name='package_recommendations')
    governance_package = models.ForeignKey(GovernancePackage, null=True, blank=True, on_delete=models.SET_NULL, related_name='recommendations')
    package_type = models.CharField(max_length=40, choices=GovernancePackageType.choices, blank=True)
    recommendation_type = models.CharField(max_length=48, choices=PackageRecommendationType.choices)
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    blockers = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['recommendation_type', '-created_at'])]

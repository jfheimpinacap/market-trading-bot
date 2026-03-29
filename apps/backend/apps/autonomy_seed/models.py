from django.db import models

from apps.common.models import TimeStampedModel


class GovernanceSeedType(models.TextChoices):
    ROADMAP_SEED = 'ROADMAP_SEED', 'Roadmap seed'
    SCENARIO_SEED = 'SCENARIO_SEED', 'Scenario seed'
    PROGRAM_SEED = 'PROGRAM_SEED', 'Program seed'
    MANAGER_SEED = 'MANAGER_SEED', 'Manager seed'
    OPERATOR_REVIEW_SEED = 'OPERATOR_REVIEW_SEED', 'Operator review seed'


class GovernanceSeedStatus(models.TextChoices):
    PENDING_REVIEW = 'PENDING_REVIEW', 'Pending review'
    READY = 'READY', 'Ready'
    REGISTERED = 'REGISTERED', 'Registered'
    BLOCKED = 'BLOCKED', 'Blocked'
    DUPLICATE_SKIPPED = 'DUPLICATE_SKIPPED', 'Duplicate skipped'
    ACKNOWLEDGED = 'ACKNOWLEDGED', 'Acknowledged'


class SeedRecommendationType(models.TextChoices):
    REGISTER_ROADMAP_SEED = 'REGISTER_ROADMAP_SEED', 'Register roadmap seed'
    REGISTER_SCENARIO_SEED = 'REGISTER_SCENARIO_SEED', 'Register scenario seed'
    REGISTER_PROGRAM_SEED = 'REGISTER_PROGRAM_SEED', 'Register program seed'
    REGISTER_MANAGER_SEED = 'REGISTER_MANAGER_SEED', 'Register manager seed'
    SKIP_DUPLICATE_SEED = 'SKIP_DUPLICATE_SEED', 'Skip duplicate seed'
    REQUIRE_MANUAL_SEED_REVIEW = 'REQUIRE_MANUAL_SEED_REVIEW', 'Require manual seed review'
    REORDER_SEED_PRIORITY = 'REORDER_SEED_PRIORITY', 'Reorder seed priority'


class GovernanceSeed(TimeStampedModel):
    governance_package = models.ForeignKey('autonomy_package.GovernancePackage', on_delete=models.CASCADE, related_name='governance_seeds')
    package_resolution = models.ForeignKey('autonomy_package_review.PackageResolution', on_delete=models.CASCADE, related_name='governance_seeds')
    seed_type = models.CharField(max_length=40, choices=GovernanceSeedType.choices)
    seed_status = models.CharField(max_length=24, choices=GovernanceSeedStatus.choices, default=GovernanceSeedStatus.PENDING_REVIEW)
    target_scope = models.CharField(max_length=24, choices=[('roadmap', 'Roadmap'), ('scenario', 'Scenario'), ('program', 'Program'), ('manager', 'Manager'), ('operator_review', 'Operator review')])
    priority_level = models.CharField(max_length=16, choices=[('LOW', 'Low'), ('MEDIUM', 'Medium'), ('HIGH', 'High'), ('CRITICAL', 'Critical')], default='MEDIUM')
    title = models.CharField(max_length=255)
    summary = models.CharField(max_length=255)
    rationale = models.CharField(max_length=255)
    linked_packages = models.JSONField(default=list, blank=True)
    linked_decisions = models.JSONField(default=list, blank=True)
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
            models.Index(fields=['governance_package', 'target_scope', '-updated_at']),
            models.Index(fields=['seed_status', '-updated_at']),
            models.Index(fields=['target_scope', 'priority_level', '-updated_at']),
        ]


class SeedRun(TimeStampedModel):
    candidate_count = models.PositiveIntegerField(default=0)
    ready_count = models.PositiveIntegerField(default=0)
    blocked_count = models.PositiveIntegerField(default=0)
    registered_count = models.PositiveIntegerField(default=0)
    duplicate_skipped_count = models.PositiveIntegerField(default=0)
    roadmap_seed_count = models.PositiveIntegerField(default=0)
    scenario_seed_count = models.PositiveIntegerField(default=0)
    program_seed_count = models.PositiveIntegerField(default=0)
    manager_seed_count = models.PositiveIntegerField(default=0)
    recommendation_summary = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class SeedRecommendation(TimeStampedModel):
    seed_run = models.ForeignKey(SeedRun, null=True, blank=True, on_delete=models.SET_NULL, related_name='recommendations')
    governance_package = models.ForeignKey('autonomy_package.GovernancePackage', null=True, blank=True, on_delete=models.SET_NULL, related_name='seed_recommendations')
    governance_seed = models.ForeignKey(GovernanceSeed, null=True, blank=True, on_delete=models.SET_NULL, related_name='recommendations')
    recommendation_type = models.CharField(max_length=48, choices=SeedRecommendationType.choices)
    seed_type = models.CharField(max_length=40, choices=GovernanceSeedType.choices, blank=True)
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    blockers = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['recommendation_type', '-created_at'])]

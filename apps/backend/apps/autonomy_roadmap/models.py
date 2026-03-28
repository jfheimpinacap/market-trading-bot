from django.db import models

from apps.autonomy_manager.models import AutonomyStage
from apps.common.models import TimeStampedModel


class DomainDependencyType(models.TextChoices):
    REQUIRES_STABLE = 'requires_stable', 'Requires stable target domain'
    BLOCKS_IF_DEGRADED = 'blocks_if_degraded', 'Blocks source if target is degraded/blocked'
    RECOMMENDED_BEFORE = 'recommended_before', 'Target should be promoted before source'
    INCOMPATIBLE_PARALLEL = 'incompatible_parallel', 'Avoid promoting both in parallel'


class DomainCriticality(models.TextChoices):
    LOW = 'LOW', 'Low'
    MEDIUM = 'MEDIUM', 'Medium'
    HIGH = 'HIGH', 'High'
    CRITICAL = 'CRITICAL', 'Critical'


class RoadmapRecommendationAction(models.TextChoices):
    PROMOTE_DOMAIN = 'PROMOTE_DOMAIN', 'Promote domain'
    HOLD_DOMAIN = 'HOLD_DOMAIN', 'Hold domain'
    FREEZE_DOMAIN = 'FREEZE_DOMAIN', 'Freeze domain'
    ROLLBACK_DOMAIN = 'ROLLBACK_DOMAIN', 'Rollback domain'
    SEQUENCE_BEFORE = 'SEQUENCE_BEFORE', 'Sequence before'
    DO_NOT_PROMOTE_IN_PARALLEL = 'DO_NOT_PROMOTE_IN_PARALLEL', 'Do not promote in parallel'
    REQUIRE_STABILIZATION_FIRST = 'REQUIRE_STABILIZATION_FIRST', 'Require stabilization first'


class RoadmapBundleRisk(models.TextChoices):
    LOW = 'LOW', 'Low'
    MEDIUM = 'MEDIUM', 'Medium'
    HIGH = 'HIGH', 'High'


class DomainDependency(TimeStampedModel):
    source_domain = models.ForeignKey('autonomy_manager.AutonomyDomain', on_delete=models.CASCADE, related_name='roadmap_dependencies_from')
    target_domain = models.ForeignKey('autonomy_manager.AutonomyDomain', on_delete=models.CASCADE, related_name='roadmap_dependencies_to')
    dependency_type = models.CharField(max_length=32, choices=DomainDependencyType.choices)
    rationale = models.CharField(max_length=255)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['source_domain__slug', 'target_domain__slug', 'dependency_type']
        unique_together = ('source_domain', 'target_domain', 'dependency_type')
        indexes = [
            models.Index(fields=['dependency_type', 'source_domain']),
            models.Index(fields=['source_domain', 'target_domain']),
        ]


class DomainRoadmapProfile(TimeStampedModel):
    domain = models.OneToOneField('autonomy_manager.AutonomyDomain', on_delete=models.CASCADE, related_name='roadmap_profile')
    criticality = models.CharField(max_length=16, choices=DomainCriticality.choices, default=DomainCriticality.MEDIUM)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['domain__slug']


class AutonomyRoadmapPlan(TimeStampedModel):
    summary = models.CharField(max_length=255)
    current_domain_posture = models.JSONField(default=dict, blank=True)
    candidate_transitions = models.JSONField(default=list, blank=True)
    blocked_domains = models.JSONField(default=list, blank=True)
    frozen_domains = models.JSONField(default=list, blank=True)
    recommended_sequence = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class RoadmapBundle(TimeStampedModel):
    plan = models.ForeignKey(AutonomyRoadmapPlan, on_delete=models.CASCADE, related_name='bundles')
    name = models.CharField(max_length=120)
    domains = models.JSONField(default=list, blank=True)
    sequence_order = models.JSONField(default=list, blank=True)
    risk_level = models.CharField(max_length=16, choices=RoadmapBundleRisk.choices, default=RoadmapBundleRisk.MEDIUM)
    requires_approval = models.BooleanField(default=False)
    rationale = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['plan_id', 'name']


class RoadmapRecommendation(TimeStampedModel):
    plan = models.ForeignKey(AutonomyRoadmapPlan, on_delete=models.CASCADE, related_name='recommendations')
    domain = models.ForeignKey('autonomy_manager.AutonomyDomain', on_delete=models.CASCADE, related_name='roadmap_recommendations')
    current_stage = models.CharField(max_length=32, choices=AutonomyStage.choices)
    proposed_stage = models.CharField(max_length=32, choices=AutonomyStage.choices, blank=True)
    action = models.CharField(max_length=48, choices=RoadmapRecommendationAction.choices)
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    evidence_refs = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['action', '-created_at']),
            models.Index(fields=['domain', '-created_at']),
        ]

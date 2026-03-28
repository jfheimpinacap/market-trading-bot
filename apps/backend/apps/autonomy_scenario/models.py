from django.db import models

from apps.common.models import TimeStampedModel


class ScenarioRecommendationCode(models.TextChoices):
    BEST_NEXT_MOVE = 'BEST_NEXT_MOVE', 'Best next move'
    SAFE_BUNDLE = 'SAFE_BUNDLE', 'Safe bundle'
    SEQUENCE_FIRST = 'SEQUENCE_FIRST', 'Sequence first'
    DELAY_UNTIL_STABLE = 'DELAY_UNTIL_STABLE', 'Delay until stable'
    DO_NOT_EXECUTE = 'DO_NOT_EXECUTE', 'Do not execute'
    REQUIRE_APPROVAL_HEAVY = 'REQUIRE_APPROVAL_HEAVY', 'Require approval heavy'


class BundleRiskLevel(models.TextChoices):
    LOW = 'LOW', 'Low'
    MEDIUM = 'MEDIUM', 'Medium'
    HIGH = 'HIGH', 'High'


class AutonomyScenarioRun(TimeStampedModel):
    summary = models.CharField(max_length=255)
    evidence_snapshot = models.JSONField(default=dict, blank=True)
    selected_option_key = models.CharField(max_length=120, blank=True)
    selected_recommendation_code = models.CharField(max_length=40, choices=ScenarioRecommendationCode.choices, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class ScenarioOption(TimeStampedModel):
    run = models.ForeignKey(AutonomyScenarioRun, on_delete=models.CASCADE, related_name='options')
    option_key = models.CharField(max_length=120)
    option_type = models.CharField(max_length=40)
    domains = models.JSONField(default=list, blank=True)
    order = models.JSONField(default=list, blank=True)
    requested_stages = models.JSONField(default=dict, blank=True)
    is_bundle = models.BooleanField(default=False)
    notes = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['run_id', 'option_key']
        unique_together = ('run', 'option_key')


class ScenarioRiskEstimate(TimeStampedModel):
    run = models.ForeignKey(AutonomyScenarioRun, on_delete=models.CASCADE, related_name='risk_estimates')
    option = models.OneToOneField(ScenarioOption, on_delete=models.CASCADE, related_name='risk_estimate')
    dependency_conflict_risk = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    approval_friction_risk = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    degraded_posture_risk = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    incident_exposure_risk = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    rollback_likelihood_hint = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    bundle_risk_level = models.CharField(max_length=16, choices=BundleRiskLevel.choices, default=BundleRiskLevel.MEDIUM)
    confidence = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    approval_heavy = models.BooleanField(default=False)
    conflicts = models.JSONField(default=list, blank=True)
    blockers = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class ScenarioRecommendation(TimeStampedModel):
    run = models.ForeignKey(AutonomyScenarioRun, on_delete=models.CASCADE, related_name='recommendations')
    option = models.ForeignKey(ScenarioOption, on_delete=models.CASCADE, related_name='recommendations')
    recommendation_code = models.CharField(max_length=40, choices=ScenarioRecommendationCode.choices)
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    supporting_evidence = models.JSONField(default=list, blank=True)
    estimated_blockers = models.JSONField(default=list, blank=True)
    score = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-score', '-created_at', '-id']
        indexes = [models.Index(fields=['recommendation_code', '-created_at'])]

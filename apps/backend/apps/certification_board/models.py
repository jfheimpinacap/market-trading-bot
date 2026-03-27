from django.db import models

from apps.common.models import TimeStampedModel


class CertificationLevel(models.TextChoices):
    NOT_CERTIFIED = 'NOT_CERTIFIED', 'Not certified'
    PAPER_CERTIFIED_DEFENSIVE = 'PAPER_CERTIFIED_DEFENSIVE', 'Paper certified (defensive)'
    PAPER_CERTIFIED_BALANCED = 'PAPER_CERTIFIED_BALANCED', 'Paper certified (balanced)'
    PAPER_CERTIFIED_HIGH_AUTONOMY = 'PAPER_CERTIFIED_HIGH_AUTONOMY', 'Paper certified (high autonomy)'
    RECERTIFICATION_REQUIRED = 'RECERTIFICATION_REQUIRED', 'Recertification required'
    REMEDIATION_REQUIRED = 'REMEDIATION_REQUIRED', 'Remediation required'


class CertificationRecommendationCode(models.TextChoices):
    HOLD_CURRENT_CERTIFICATION = 'HOLD_CURRENT_CERTIFICATION', 'Hold current certification'
    UPGRADE_PAPER_AUTONOMY = 'UPGRADE_PAPER_AUTONOMY', 'Upgrade paper autonomy'
    DOWNGRADE_TO_DEFENSIVE = 'DOWNGRADE_TO_DEFENSIVE', 'Downgrade to defensive'
    REQUIRE_REMEDIATION = 'REQUIRE_REMEDIATION', 'Require remediation'
    REQUIRE_RECERTIFICATION = 'REQUIRE_RECERTIFICATION', 'Require recertification'
    MANUAL_REVIEW_REQUIRED = 'MANUAL_REVIEW_REQUIRED', 'Manual review required'


class CertificationRunStatus(models.TextChoices):
    COMPLETED = 'COMPLETED', 'Completed'
    FAILED = 'FAILED', 'Failed'


class OperatingEnvelope(TimeStampedModel):
    max_autonomy_mode_allowed = models.CharField(max_length=32, default='PAPER_ASSIST')
    max_new_entries_per_cycle = models.PositiveIntegerField(default=1)
    max_size_multiplier_allowed = models.DecimalField(max_digits=8, decimal_places=4, default=1)
    auto_execution_allowed = models.BooleanField(default=False)
    canary_rollout_allowed = models.BooleanField(default=False)
    aggressive_profiles_disallowed = models.BooleanField(default=True)
    defensive_profiles_only = models.BooleanField(default=True)
    allowed_profiles = models.JSONField(default=list, blank=True)
    constrained_modules = models.JSONField(default=list, blank=True)
    notes = models.TextField(blank=True)
    constraints = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class CertificationEvidenceSnapshot(TimeStampedModel):
    readiness_summary = models.JSONField(default=dict, blank=True)
    execution_evaluation_summary = models.JSONField(default=dict, blank=True)
    champion_challenger_summary = models.JSONField(default=dict, blank=True)
    promotion_summary = models.JSONField(default=dict, blank=True)
    rollout_summary = models.JSONField(default=dict, blank=True)
    incident_summary = models.JSONField(default=dict, blank=True)
    chaos_benchmark_summary = models.JSONField(default=dict, blank=True)
    portfolio_governor_summary = models.JSONField(default=dict, blank=True)
    profile_manager_summary = models.JSONField(default=dict, blank=True)
    runtime_safety_summary = models.JSONField(default=dict, blank=True)
    degraded_or_rollback_summary = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class CertificationRun(TimeStampedModel):
    status = models.CharField(max_length=16, choices=CertificationRunStatus.choices, default=CertificationRunStatus.COMPLETED)
    decision_mode = models.CharField(max_length=24, default='RECOMMENDATION_ONLY')
    certification_level = models.CharField(max_length=48, choices=CertificationLevel.choices, default=CertificationLevel.NOT_CERTIFIED)
    recommendation_code = models.CharField(max_length=40, choices=CertificationRecommendationCode.choices)
    confidence = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    rationale = models.TextField(blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    blocking_constraints = models.JSONField(default=list, blank=True)
    remediation_items = models.JSONField(default=list, blank=True)
    evidence_summary = models.JSONField(default=dict, blank=True)
    summary = models.CharField(max_length=255, blank=True)
    evidence_snapshot = models.ForeignKey(CertificationEvidenceSnapshot, on_delete=models.PROTECT, related_name='certification_runs')
    operating_envelope = models.ForeignKey(OperatingEnvelope, on_delete=models.PROTECT, related_name='certification_runs')
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class CertificationDecisionLog(TimeStampedModel):
    run = models.ForeignKey(CertificationRun, on_delete=models.CASCADE, related_name='decision_logs')
    event_type = models.CharField(max_length=32, default='RECOMMENDATION_ISSUED')
    actor = models.CharField(max_length=64, default='certification_board')
    notes = models.TextField(blank=True)
    payload = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']

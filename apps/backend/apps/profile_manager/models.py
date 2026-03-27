from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel


class RegimeClassification(models.TextChoices):
    NORMAL = 'NORMAL', 'Normal'
    CAUTION = 'CAUTION', 'Caution'
    STRESSED = 'STRESSED', 'Stressed'
    CONCENTRATED = 'CONCENTRATED', 'Concentrated'
    DRAWDOWN_MODE = 'DRAWDOWN_MODE', 'Drawdown mode'
    DEFENSIVE = 'DEFENSIVE', 'Defensive'
    BLOCKED = 'BLOCKED', 'Blocked'


class ProfileDecisionMode(models.TextChoices):
    RECOMMEND_ONLY = 'RECOMMEND_ONLY', 'Recommend only'
    APPLY_SAFE = 'APPLY_SAFE', 'Apply safe'
    APPLY_FORCED = 'APPLY_FORCED', 'Apply forced'


class ProfileGovernanceRunStatus(models.TextChoices):
    RUNNING = 'RUNNING', 'Running'
    COMPLETED = 'COMPLETED', 'Completed'
    FAILED = 'FAILED', 'Failed'


class ManagedProfileBinding(TimeStampedModel):
    module_key = models.CharField(max_length=64)
    operating_mode = models.CharField(max_length=24, help_text='conservative, balanced, aggressive_light')
    profile_slug = models.CharField(max_length=96)
    profile_label = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['module_key', 'operating_mode', 'id']
        constraints = [
            models.UniqueConstraint(fields=['module_key', 'operating_mode'], name='profile_binding_unique_module_mode'),
        ]


class ProfileGovernanceRun(TimeStampedModel):
    status = models.CharField(max_length=16, choices=ProfileGovernanceRunStatus.choices, default=ProfileGovernanceRunStatus.RUNNING)
    regime = models.CharField(max_length=24, choices=RegimeClassification.choices, default=RegimeClassification.NORMAL)
    runtime_mode = models.CharField(max_length=32, blank=True)
    readiness_status = models.CharField(max_length=24, blank=True)
    safety_status = models.CharField(max_length=24, blank=True)
    triggered_by = models.CharField(max_length=64, default='manual_api')
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)
    summary = models.CharField(max_length=255, blank=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']


class ProfileDecision(TimeStampedModel):
    run = models.OneToOneField(ProfileGovernanceRun, on_delete=models.CASCADE, related_name='decision')
    decision_mode = models.CharField(max_length=20, choices=ProfileDecisionMode.choices, default=ProfileDecisionMode.RECOMMEND_ONLY)

    target_research_profile = models.CharField(max_length=96)
    target_signal_profile = models.CharField(max_length=96)
    target_opportunity_supervisor_profile = models.CharField(max_length=96)
    target_mission_control_profile = models.CharField(max_length=96)
    target_portfolio_governor_profile = models.CharField(max_length=96)
    target_prediction_profile = models.CharField(max_length=96, blank=True)

    rationale = models.TextField(blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    blocking_constraints = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    is_applied = models.BooleanField(default=False)
    applied_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']

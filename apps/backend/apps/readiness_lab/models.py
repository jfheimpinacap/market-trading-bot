from django.db import models

from apps.common.models import TimeStampedModel


class ReadinessProfileType(models.TextChoices):
    CONSERVATIVE = 'conservative', 'Conservative'
    BALANCED = 'balanced', 'Balanced'
    STRICT = 'strict', 'Strict'
    CUSTOM = 'custom', 'Custom'


class ReadinessStatus(models.TextChoices):
    READY = 'READY', 'Ready'
    CAUTION = 'CAUTION', 'Caution'
    NOT_READY = 'NOT_READY', 'Not ready'


class ReadinessProfile(TimeStampedModel):
    name = models.CharField(max_length=96)
    slug = models.SlugField(max_length=128, unique=True)
    description = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    profile_type = models.CharField(max_length=24, choices=ReadinessProfileType.choices, default=ReadinessProfileType.BALANCED)
    config = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['name', 'id']
        indexes = [
            models.Index(fields=['is_active', 'profile_type']),
        ]


class ReadinessAssessmentRun(TimeStampedModel):
    readiness_profile = models.ForeignKey(ReadinessProfile, on_delete=models.CASCADE, related_name='assessment_runs')
    status = models.CharField(max_length=16, choices=ReadinessStatus.choices, default=ReadinessStatus.CAUTION)
    overall_score = models.DecimalField(max_digits=7, decimal_places=4, null=True, blank=True)
    summary = models.CharField(max_length=255, blank=True)
    rationale = models.TextField(blank=True)
    gates_passed_count = models.PositiveIntegerField(default=0)
    gates_failed_count = models.PositiveIntegerField(default=0)
    warnings_count = models.PositiveIntegerField(default=0)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['readiness_profile', '-created_at']),
        ]

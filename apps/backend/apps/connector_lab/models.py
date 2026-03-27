from django.db import models

from apps.common.models import TimeStampedModel


class AdapterQualificationStatus(models.TextChoices):
    RUNNING = 'RUNNING', 'Running'
    SUCCESS = 'SUCCESS', 'Success'
    PARTIAL = 'PARTIAL', 'Partial'
    FAILED = 'FAILED', 'Failed'


class AdapterQualificationCaseStatus(models.TextChoices):
    PASSED = 'PASSED', 'Passed'
    FAILED = 'FAILED', 'Failed'
    UNSUPPORTED = 'UNSUPPORTED', 'Unsupported'
    WARNING = 'WARNING', 'Warning'


class AdapterReadinessCode(models.TextChoices):
    SANDBOX_CERTIFIED = 'SANDBOX_CERTIFIED', 'Sandbox certified'
    READ_ONLY_PREPARED = 'READ_ONLY_PREPARED', 'Read-only prepared'
    INCOMPLETE_MAPPING = 'INCOMPLETE_MAPPING', 'Incomplete mapping'
    RECONCILIATION_GAPS = 'RECONCILIATION_GAPS', 'Reconciliation gaps'
    MANUAL_REVIEW_REQUIRED = 'MANUAL_REVIEW_REQUIRED', 'Manual review required'
    NOT_READY = 'NOT_READY', 'Not ready'


class ConnectorFixtureProfile(TimeStampedModel):
    slug = models.SlugField(max_length=64, unique=True)
    display_name = models.CharField(max_length=96)
    description = models.CharField(max_length=255)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['slug']


class AdapterQualificationRun(TimeStampedModel):
    adapter_name = models.CharField(max_length=64)
    adapter_type = models.CharField(max_length=64, default='sandbox')
    fixture_profile = models.ForeignKey(
        ConnectorFixtureProfile,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='qualification_runs',
    )
    qualification_status = models.CharField(max_length=16, choices=AdapterQualificationStatus.choices, default=AdapterQualificationStatus.RUNNING)
    capability_checks_run = models.PositiveIntegerField(default=0)
    payload_checks_run = models.PositiveIntegerField(default=0)
    response_checks_run = models.PositiveIntegerField(default=0)
    account_mirror_checks_run = models.PositiveIntegerField(default=0)
    reconciliation_checks_run = models.PositiveIntegerField(default=0)
    summary = models.CharField(max_length=255, blank=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class AdapterQualificationResult(TimeStampedModel):
    qualification_run = models.ForeignKey(AdapterQualificationRun, on_delete=models.CASCADE, related_name='results')
    case_code = models.CharField(max_length=64)
    case_group = models.CharField(max_length=32)
    result_status = models.CharField(max_length=16, choices=AdapterQualificationCaseStatus.choices)
    issues = models.JSONField(default=list, blank=True)
    warnings = models.JSONField(default=list, blank=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['id']
        indexes = [models.Index(fields=['case_code', 'result_status'])]


class AdapterReadinessRecommendation(TimeStampedModel):
    qualification_run = models.OneToOneField(AdapterQualificationRun, on_delete=models.CASCADE, related_name='readiness_recommendation')
    recommendation = models.CharField(max_length=32, choices=AdapterReadinessCode.choices, default=AdapterReadinessCode.NOT_READY)
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    missing_capabilities = models.JSONField(default=list, blank=True)
    unsupported_paths = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']

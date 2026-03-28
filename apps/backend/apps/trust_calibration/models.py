from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel


class TrustCalibrationRunStatus(models.TextChoices):
    READY = 'READY', 'Ready'
    IN_PROGRESS = 'IN_PROGRESS', 'In progress'
    FAILED = 'FAILED', 'Failed'


class TrustCalibrationRecommendationType(models.TextChoices):
    PROMOTE_TO_SAFE_AUTOMATION = 'PROMOTE_TO_SAFE_AUTOMATION', 'Promote to safe automation'
    KEEP_APPROVAL_REQUIRED = 'KEEP_APPROVAL_REQUIRED', 'Keep approval required'
    DOWNGRADE_TO_MANUAL_ONLY = 'DOWNGRADE_TO_MANUAL_ONLY', 'Downgrade to manual only'
    BLOCK_AUTOMATION_FOR_ACTION = 'BLOCK_AUTOMATION_FOR_ACTION', 'Block automation for action'
    REQUIRE_MORE_DATA = 'REQUIRE_MORE_DATA', 'Require more data'
    REVIEW_RULE_CONDITIONS = 'REVIEW_RULE_CONDITIONS', 'Review rule conditions'


class TrustCalibrationRun(TimeStampedModel):
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=TrustCalibrationRunStatus.choices, default=TrustCalibrationRunStatus.IN_PROGRESS)
    window_days = models.PositiveIntegerField(default=30)
    source_type = models.CharField(max_length=80, blank=True)
    runbook_template_slug = models.CharField(max_length=120, blank=True)
    profile_slug = models.CharField(max_length=80, blank=True)
    include_degraded = models.BooleanField(default=True)
    summary = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']
        indexes = [models.Index(fields=['status', '-started_at'])]


class AutomationFeedbackSnapshot(TimeStampedModel):
    run = models.ForeignKey(TrustCalibrationRun, on_delete=models.CASCADE, related_name='feedback_snapshots')
    action_type = models.CharField(max_length=80)
    source_type = models.CharField(max_length=80, blank=True)
    runbook_template_slug = models.CharField(max_length=120, blank=True)
    profile_slug = models.CharField(max_length=80, blank=True)
    current_trust_tier = models.CharField(max_length=32, blank=True)

    approvals_granted = models.PositiveIntegerField(default=0)
    approvals_rejected = models.PositiveIntegerField(default=0)
    approvals_expired = models.PositiveIntegerField(default=0)
    approvals_escalated = models.PositiveIntegerField(default=0)
    auto_actions_executed = models.PositiveIntegerField(default=0)
    auto_actions_failed = models.PositiveIntegerField(default=0)
    blocked_decisions = models.PositiveIntegerField(default=0)
    retry_count = models.PositiveIntegerField(default=0)
    operator_overrides = models.PositiveIntegerField(default=0)
    incidents_after_auto = models.PositiveIntegerField(default=0)

    metrics = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-id']
        indexes = [models.Index(fields=['run', 'action_type'])]


class TrustCalibrationRecommendation(TimeStampedModel):
    run = models.ForeignKey(TrustCalibrationRun, on_delete=models.CASCADE, related_name='recommendations')
    snapshot = models.ForeignKey(AutomationFeedbackSnapshot, on_delete=models.CASCADE, related_name='recommendations')
    recommendation_type = models.CharField(max_length=48, choices=TrustCalibrationRecommendationType.choices)
    action_type = models.CharField(max_length=80)
    current_trust_tier = models.CharField(max_length=32, blank=True)
    recommended_trust_tier = models.CharField(max_length=32, blank=True)
    confidence = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    supporting_metrics = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-confidence', '-id']
        indexes = [models.Index(fields=['run', 'recommendation_type'])]

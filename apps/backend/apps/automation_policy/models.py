from django.db import models

from apps.common.models import TimeStampedModel


class AutomationTrustTier(models.TextChoices):
    MANUAL_ONLY = 'MANUAL_ONLY', 'Manual only'
    APPROVAL_REQUIRED = 'APPROVAL_REQUIRED', 'Approval required'
    SAFE_AUTOMATION = 'SAFE_AUTOMATION', 'Safe automation'
    AUTO_BLOCKED = 'AUTO_BLOCKED', 'Auto blocked'


class AutomationDecisionOutcome(models.TextChoices):
    ALLOWED = 'ALLOWED', 'Allowed'
    APPROVAL_REQUIRED = 'APPROVAL_REQUIRED', 'Approval required'
    MANUAL_ONLY = 'MANUAL_ONLY', 'Manual only'
    BLOCKED = 'BLOCKED', 'Blocked'


class AutomationActionExecutionStatus(models.TextChoices):
    EXECUTED = 'EXECUTED', 'Executed'
    SKIPPED = 'SKIPPED', 'Skipped'
    FAILED = 'FAILED', 'Failed'


class AutomationPolicyProfile(TimeStampedModel):
    slug = models.SlugField(max_length=80, unique=True)
    name = models.CharField(max_length=120)
    description = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=False)
    is_default = models.BooleanField(default=False)
    recommendation_mode = models.BooleanField(default=False)
    allow_runbook_auto_advance = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['name', 'id']


class AutomationPolicyRule(TimeStampedModel):
    profile = models.ForeignKey(AutomationPolicyProfile, on_delete=models.CASCADE, related_name='rules')
    action_type = models.CharField(max_length=80)
    source_context_type = models.CharField(max_length=80, blank=True)
    trust_tier = models.CharField(max_length=32, choices=AutomationTrustTier.choices)
    conditions = models.JSONField(default=dict, blank=True)
    rationale = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['profile_id', 'action_type', 'source_context_type', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['profile', 'action_type', 'source_context_type'],
                name='automation_policy_rule_unique_profile_action_context',
            ),
        ]


class AutomationDecision(TimeStampedModel):
    profile = models.ForeignKey(AutomationPolicyProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='decisions')
    rule = models.ForeignKey(AutomationPolicyRule, on_delete=models.SET_NULL, null=True, blank=True, related_name='decisions')
    action_type = models.CharField(max_length=80)
    source_context_type = models.CharField(max_length=80, blank=True)
    runbook_instance_id = models.PositiveIntegerField(null=True, blank=True)
    runbook_step_id = models.PositiveIntegerField(null=True, blank=True)
    trust_tier = models.CharField(max_length=32, choices=AutomationTrustTier.choices)
    effective_trust_tier = models.CharField(max_length=32, choices=AutomationTrustTier.choices)
    outcome = models.CharField(max_length=24, choices=AutomationDecisionOutcome.choices)
    reason_codes = models.JSONField(default=list, blank=True)
    rationale = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['action_type', '-created_at']),
            models.Index(fields=['outcome', '-created_at']),
            models.Index(fields=['effective_trust_tier', '-created_at']),
        ]


class AutomationActionLog(TimeStampedModel):
    decision = models.ForeignKey(AutomationDecision, on_delete=models.CASCADE, related_name='action_logs')
    source_runbook_instance_id = models.PositiveIntegerField(null=True, blank=True)
    source_runbook_step_id = models.PositiveIntegerField(null=True, blank=True)
    action_name = models.CharField(max_length=120)
    execution_status = models.CharField(max_length=20, choices=AutomationActionExecutionStatus.choices)
    result_summary = models.CharField(max_length=255, blank=True)
    output_refs = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['execution_status', '-created_at']),
            models.Index(fields=['action_name', '-created_at']),
        ]

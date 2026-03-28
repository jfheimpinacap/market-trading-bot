from django.db import models

from apps.common.models import TimeStampedModel


class PolicyTuningCandidateStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    PENDING_APPROVAL = 'PENDING_APPROVAL', 'Pending approval'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'
    APPLIED = 'APPLIED', 'Applied'
    SUPERSEDED = 'SUPERSEDED', 'Superseded'


class PolicyTuningReviewDecision(models.TextChoices):
    APPROVE = 'APPROVE', 'Approve'
    REJECT = 'REJECT', 'Reject'
    REQUIRE_MORE_EVIDENCE = 'REQUIRE_MORE_EVIDENCE', 'Require more evidence'
    DEFER = 'DEFER', 'Defer'


class PolicyTuningCandidate(TimeStampedModel):
    recommendation = models.ForeignKey(
        'trust_calibration.TrustCalibrationRecommendation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='policy_tuning_candidates',
    )
    approval_request = models.OneToOneField(
        'approval_center.ApprovalRequest',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='policy_tuning_candidate',
    )
    action_type = models.CharField(max_length=80)
    current_profile = models.ForeignKey(
        'automation_policy.AutomationPolicyProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='policy_tuning_candidates',
    )
    current_rule = models.ForeignKey(
        'automation_policy.AutomationPolicyRule',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='policy_tuning_candidates',
    )
    current_trust_tier = models.CharField(max_length=32, blank=True)
    proposed_trust_tier = models.CharField(max_length=32, blank=True)
    proposed_conditions = models.JSONField(default=dict, blank=True)
    rationale = models.CharField(max_length=255, blank=True)
    confidence = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    evidence_refs = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=24, choices=PolicyTuningCandidateStatus.choices, default=PolicyTuningCandidateStatus.DRAFT)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['action_type', '-created_at']),
        ]


class PolicyChangeSet(TimeStampedModel):
    candidate = models.OneToOneField(PolicyTuningCandidate, on_delete=models.CASCADE, related_name='change_set')
    profile_slug = models.SlugField(max_length=80)
    action_type = models.CharField(max_length=80)
    old_trust_tier = models.CharField(max_length=32, blank=True)
    new_trust_tier = models.CharField(max_length=32, blank=True)
    old_conditions = models.JSONField(default=dict, blank=True)
    new_conditions = models.JSONField(default=dict, blank=True)
    apply_scope = models.CharField(max_length=80, default='RULE_ONLY')
    notes = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class PolicyTuningReview(TimeStampedModel):
    candidate = models.ForeignKey(PolicyTuningCandidate, on_delete=models.CASCADE, related_name='reviews')
    decision = models.CharField(max_length=32, choices=PolicyTuningReviewDecision.choices)
    review_status = models.CharField(max_length=16, default='COMPLETED')
    reviewer_note = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class PolicyTuningApplicationLog(TimeStampedModel):
    candidate = models.ForeignKey(PolicyTuningCandidate, on_delete=models.CASCADE, related_name='application_logs')
    applied_to_profile = models.ForeignKey('automation_policy.AutomationPolicyProfile', on_delete=models.SET_NULL, null=True, blank=True)
    applied_to_rule = models.ForeignKey('automation_policy.AutomationPolicyRule', on_delete=models.SET_NULL, null=True, blank=True)
    before_snapshot = models.JSONField(default=dict, blank=True)
    after_snapshot = models.JSONField(default=dict, blank=True)
    applied_at = models.DateTimeField()
    result_summary = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-applied_at', '-id']
        indexes = [models.Index(fields=['-applied_at'])]

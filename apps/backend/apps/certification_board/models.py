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


class StabilizationReadiness(models.TextChoices):
    READY = 'READY', 'Ready'
    NEEDS_OBSERVATION = 'NEEDS_OBSERVATION', 'Needs observation'
    REVIEW_REQUIRED = 'REVIEW_REQUIRED', 'Review required'
    ROLLBACK_RECOMMENDED = 'ROLLBACK_RECOMMENDED', 'Rollback recommended'
    BLOCKED = 'BLOCKED', 'Blocked'


class CertificationEvidenceStatus(models.TextChoices):
    STRONG = 'STRONG', 'Strong'
    MIXED = 'MIXED', 'Mixed'
    WEAK = 'WEAK', 'Weak'
    INSUFFICIENT = 'INSUFFICIENT', 'Insufficient'


class CertificationDecisionStatus(models.TextChoices):
    CERTIFIED_FOR_PAPER_BASELINE = 'CERTIFIED_FOR_PAPER_BASELINE', 'Certified for paper baseline'
    KEEP_UNDER_OBSERVATION = 'KEEP_UNDER_OBSERVATION', 'Keep under observation'
    REQUIRE_MANUAL_REVIEW = 'REQUIRE_MANUAL_REVIEW', 'Require manual review'
    RECOMMEND_ROLLBACK = 'RECOMMEND_ROLLBACK', 'Recommend rollback'
    REJECT_CERTIFICATION = 'REJECT_CERTIFICATION', 'Reject certification'


class CertificationRecommendationType(models.TextChoices):
    CERTIFY_FOR_PAPER_BASELINE = 'CERTIFY_FOR_PAPER_BASELINE', 'Certify for paper baseline'
    KEEP_UNDER_OBSERVATION = 'KEEP_UNDER_OBSERVATION', 'Keep under observation'
    REQUIRE_MORE_OBSERVATION = 'REQUIRE_MORE_OBSERVATION', 'Require more observation'
    REQUIRE_MANUAL_CERTIFICATION_REVIEW = 'REQUIRE_MANUAL_CERTIFICATION_REVIEW', 'Require manual certification review'
    RECOMMEND_MANUAL_ROLLBACK = 'RECOMMEND_MANUAL_ROLLBACK', 'Recommend manual rollback'
    REJECT_CERTIFICATION = 'REJECT_CERTIFICATION', 'Reject certification'
    REORDER_CERTIFICATION_PRIORITY = 'REORDER_CERTIFICATION_PRIORITY', 'Reorder certification priority'


class RolloutCertificationRun(TimeStampedModel):
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    linked_rollout_execution_run = models.ForeignKey(
        'promotion_committee.RolloutExecutionRun',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='certification_runs',
    )
    candidate_count = models.PositiveIntegerField(default=0)
    certified_count = models.PositiveIntegerField(default=0)
    observation_count = models.PositiveIntegerField(default=0)
    review_required_count = models.PositiveIntegerField(default=0)
    rollback_recommended_count = models.PositiveIntegerField(default=0)
    rejected_count = models.PositiveIntegerField(default=0)
    recommendation_summary = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']


class CertificationCandidate(TimeStampedModel):
    review_run = models.ForeignKey(RolloutCertificationRun, on_delete=models.CASCADE, related_name='candidates')
    linked_rollout_execution = models.ForeignKey(
        'promotion_committee.RolloutExecutionRecord', on_delete=models.CASCADE, related_name='certification_candidates'
    )
    linked_post_rollout_status = models.ForeignKey(
        'promotion_committee.PostRolloutStatus',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='certification_candidates',
    )
    linked_rollout_plan = models.ForeignKey(
        'promotion_committee.ManualRolloutPlan', on_delete=models.CASCADE, related_name='certification_candidates'
    )
    linked_promotion_case = models.ForeignKey(
        'promotion_committee.PromotionCase',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='certification_candidates',
    )
    target_component = models.CharField(max_length=32)
    target_scope = models.CharField(max_length=24)
    rollout_status = models.CharField(max_length=24)
    stabilization_readiness = models.CharField(
        max_length=24, choices=StabilizationReadiness.choices, default=StabilizationReadiness.NEEDS_OBSERVATION
    )
    blockers = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['stabilization_readiness', '-created_at'])]


class CertificationEvidencePack(TimeStampedModel):
    linked_candidate = models.OneToOneField(
        CertificationCandidate, on_delete=models.CASCADE, related_name='evidence_pack'
    )
    summary = models.CharField(max_length=255)
    linked_checkpoint_outcomes = models.JSONField(default=list, blank=True)
    linked_post_rollout_statuses = models.JSONField(default=list, blank=True)
    linked_evaluation_metrics = models.JSONField(default=dict, blank=True)
    sample_count = models.PositiveIntegerField(default=0)
    confidence_score = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    stability_score = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    regression_risk_score = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    evidence_status = models.CharField(
        max_length=16, choices=CertificationEvidenceStatus.choices, default=CertificationEvidenceStatus.INSUFFICIENT
    )
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['evidence_status', '-created_at'])]


class CertificationDecision(TimeStampedModel):
    linked_candidate = models.OneToOneField(CertificationCandidate, on_delete=models.CASCADE, related_name='decision')
    linked_evidence_pack = models.ForeignKey(
        CertificationEvidencePack, on_delete=models.CASCADE, related_name='decisions'
    )
    decision_status = models.CharField(max_length=40, choices=CertificationDecisionStatus.choices)
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    blockers = models.JSONField(default=list, blank=True)
    decided_by = models.CharField(max_length=120, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['decision_status', '-created_at'])]


class CertificationRecommendation(TimeStampedModel):
    review_run = models.ForeignKey(RolloutCertificationRun, on_delete=models.CASCADE, related_name='recommendations')
    target_candidate = models.ForeignKey(
        CertificationCandidate, null=True, blank=True, on_delete=models.SET_NULL, related_name='recommendations'
    )
    recommendation_type = models.CharField(max_length=48, choices=CertificationRecommendationType.choices)
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    blockers = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['recommendation_type', '-created_at'])]


class BaselineBindingResolutionStatus(models.TextChoices):
    RESOLVED = 'RESOLVED', 'Resolved'
    PARTIAL = 'PARTIAL', 'Partial'
    BLOCKED = 'BLOCKED', 'Blocked'
    UNKNOWN = 'UNKNOWN', 'Unknown'


class PaperBaselineConfirmationStatus(models.TextChoices):
    PROPOSED = 'PROPOSED', 'Proposed'
    READY_TO_CONFIRM = 'READY_TO_CONFIRM', 'Ready to confirm'
    CONFIRMED = 'CONFIRMED', 'Confirmed'
    BLOCKED = 'BLOCKED', 'Blocked'
    DEFERRED = 'DEFERRED', 'Deferred'
    ROLLBACK_AVAILABLE = 'ROLLBACK_AVAILABLE', 'Rollback available'


class BaselineBindingType(models.TextChoices):
    CHAMPION_REFERENCE = 'champion_reference', 'Champion reference'
    STACK_PROFILE_BINDING = 'stack_profile_binding', 'Stack profile binding'
    TRUST_CALIBRATION_BINDING = 'trust_calibration_binding', 'Trust calibration binding'
    POLICY_TUNING_BINDING = 'policy_tuning_binding', 'Policy tuning binding'
    ROLLOUT_REFERENCE = 'rollout_reference', 'Rollout reference'


class BaselineBindingStatus(models.TextChoices):
    PREVIOUS = 'PREVIOUS', 'Previous'
    PROPOSED = 'PROPOSED', 'Proposed'
    CONFIRMED = 'CONFIRMED', 'Confirmed'
    REVERTED = 'REVERTED', 'Reverted'


class BaselineConfirmationRecommendationType(models.TextChoices):
    CONFIRM_PAPER_BASELINE = 'CONFIRM_PAPER_BASELINE', 'Confirm paper baseline'
    REQUIRE_BINDING_REVIEW = 'REQUIRE_BINDING_REVIEW', 'Require binding review'
    DEFER_BASELINE_CONFIRMATION = 'DEFER_BASELINE_CONFIRMATION', 'Defer baseline confirmation'
    PREPARE_BASELINE_ROLLBACK = 'PREPARE_BASELINE_ROLLBACK', 'Prepare baseline rollback'
    REQUIRE_COMMITTEE_RECHECK = 'REQUIRE_COMMITTEE_RECHECK', 'Require committee recheck'
    REORDER_BASELINE_PRIORITY = 'REORDER_BASELINE_PRIORITY', 'Reorder baseline priority'


class BaselineConfirmationRun(TimeStampedModel):
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    linked_certification_run = models.ForeignKey(
        RolloutCertificationRun,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='baseline_confirmation_runs',
    )
    candidate_count = models.PositiveIntegerField(default=0)
    ready_to_confirm_count = models.PositiveIntegerField(default=0)
    blocked_count = models.PositiveIntegerField(default=0)
    confirmed_count = models.PositiveIntegerField(default=0)
    rollback_ready_count = models.PositiveIntegerField(default=0)
    recommendation_summary = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']


class BaselineConfirmationCandidate(TimeStampedModel):
    review_run = models.ForeignKey(BaselineConfirmationRun, on_delete=models.CASCADE, related_name='candidates')
    linked_certification_decision = models.ForeignKey(
        CertificationDecision, on_delete=models.CASCADE, related_name='baseline_confirmation_candidates'
    )
    linked_certification_candidate = models.ForeignKey(
        CertificationCandidate, on_delete=models.CASCADE, related_name='baseline_confirmation_candidates'
    )
    linked_rollout_execution = models.ForeignKey(
        'promotion_committee.RolloutExecutionRecord',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='baseline_confirmation_candidates',
    )
    target_component = models.CharField(max_length=32)
    target_scope = models.CharField(max_length=24)
    certification_status = models.CharField(max_length=40, choices=CertificationDecisionStatus.choices)
    previous_baseline_reference = models.CharField(max_length=255, blank=True)
    proposed_baseline_reference = models.CharField(max_length=255, blank=True)
    binding_resolution_status = models.CharField(
        max_length=16, choices=BaselineBindingResolutionStatus.choices, default=BaselineBindingResolutionStatus.UNKNOWN
    )
    ready_for_confirmation = models.BooleanField(default=False)
    blockers = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['binding_resolution_status', '-created_at'])]


class PaperBaselineConfirmation(TimeStampedModel):
    linked_candidate = models.OneToOneField(
        BaselineConfirmationCandidate, on_delete=models.CASCADE, related_name='baseline_confirmation'
    )
    linked_certification_decision = models.ForeignKey(
        CertificationDecision, on_delete=models.CASCADE, related_name='paper_baseline_confirmations'
    )
    confirmation_status = models.CharField(
        max_length=24, choices=PaperBaselineConfirmationStatus.choices, default=PaperBaselineConfirmationStatus.PROPOSED
    )
    target_component = models.CharField(max_length=32)
    target_scope = models.CharField(max_length=24)
    previous_baseline_snapshot = models.JSONField(default=dict, blank=True)
    confirmed_baseline_snapshot = models.JSONField(default=dict, blank=True)
    confirmed_by = models.CharField(max_length=120, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    blockers = models.JSONField(default=list, blank=True)
    linked_binding_artifact = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['confirmation_status', '-created_at'])]


class BaselineBindingSnapshot(TimeStampedModel):
    linked_confirmation = models.ForeignKey(
        PaperBaselineConfirmation, on_delete=models.CASCADE, related_name='binding_snapshots'
    )
    binding_type = models.CharField(max_length=40, choices=BaselineBindingType.choices)
    binding_status = models.CharField(max_length=16, choices=BaselineBindingStatus.choices)
    binding_snapshot = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['binding_type', 'binding_status', '-created_at'])]


class BaselineConfirmationRecommendation(TimeStampedModel):
    review_run = models.ForeignKey(
        BaselineConfirmationRun, on_delete=models.CASCADE, related_name='recommendations'
    )
    target_confirmation = models.ForeignKey(
        PaperBaselineConfirmation,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='recommendations',
    )
    recommendation_type = models.CharField(max_length=48, choices=BaselineConfirmationRecommendationType.choices)
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    blockers = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['recommendation_type', '-created_at'])]


class PaperBaselineActivationStatus(models.TextChoices):
    PROPOSED = 'PROPOSED', 'Proposed'
    READY_TO_ACTIVATE = 'READY_TO_ACTIVATE', 'Ready to activate'
    ACTIVATED = 'ACTIVATED', 'Activated'
    BLOCKED = 'BLOCKED', 'Blocked'
    DEFERRED = 'DEFERRED', 'Deferred'
    ROLLBACK_AVAILABLE = 'ROLLBACK_AVAILABLE', 'Rollback available'


class ActivePaperBindingStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Active'
    SUPERSEDED = 'SUPERSEDED', 'Superseded'
    REVERTED = 'REVERTED', 'Reverted'


class BaselineActivationRecommendationType(models.TextChoices):
    ACTIVATE_PAPER_BASELINE = 'ACTIVATE_PAPER_BASELINE', 'Activate paper baseline'
    REQUIRE_BINDING_RECHECK = 'REQUIRE_BINDING_RECHECK', 'Require binding recheck'
    DEFER_ACTIVATION = 'DEFER_ACTIVATION', 'Defer activation'
    PREPARE_ACTIVATION_ROLLBACK = 'PREPARE_ACTIVATION_ROLLBACK', 'Prepare activation rollback'
    REQUIRE_COMMITTEE_RECHECK = 'REQUIRE_COMMITTEE_RECHECK', 'Require committee recheck'
    REORDER_ACTIVATION_PRIORITY = 'REORDER_ACTIVATION_PRIORITY', 'Reorder activation priority'


class BaselineActivationRun(TimeStampedModel):
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    linked_baseline_confirmation_run = models.ForeignKey(
        BaselineConfirmationRun,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='baseline_activation_runs',
    )
    candidate_count = models.PositiveIntegerField(default=0)
    ready_to_activate_count = models.PositiveIntegerField(default=0)
    blocked_count = models.PositiveIntegerField(default=0)
    activated_count = models.PositiveIntegerField(default=0)
    rollback_ready_count = models.PositiveIntegerField(default=0)
    recommendation_summary = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']


class BaselineActivationCandidate(TimeStampedModel):
    review_run = models.ForeignKey(BaselineActivationRun, on_delete=models.CASCADE, related_name='candidates')
    linked_paper_baseline_confirmation = models.ForeignKey(
        PaperBaselineConfirmation, on_delete=models.CASCADE, related_name='activation_candidates'
    )
    linked_certification_decision = models.ForeignKey(
        CertificationDecision,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='baseline_activation_candidates',
    )
    target_component = models.CharField(max_length=32)
    target_scope = models.CharField(max_length=24)
    previous_active_reference = models.CharField(max_length=255, blank=True)
    proposed_active_reference = models.CharField(max_length=255, blank=True)
    activation_resolution_status = models.CharField(
        max_length=16, choices=BaselineBindingResolutionStatus.choices, default=BaselineBindingResolutionStatus.UNKNOWN
    )
    ready_for_activation = models.BooleanField(default=False)
    blockers = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['activation_resolution_status', '-created_at'])]


class PaperBaselineActivation(TimeStampedModel):
    linked_candidate = models.ForeignKey(
        BaselineActivationCandidate,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='activations',
    )
    linked_confirmation = models.ForeignKey(
        PaperBaselineConfirmation, on_delete=models.CASCADE, related_name='activations'
    )
    activation_status = models.CharField(
        max_length=24, choices=PaperBaselineActivationStatus.choices, default=PaperBaselineActivationStatus.PROPOSED
    )
    target_component = models.CharField(max_length=32)
    target_scope = models.CharField(max_length=24)
    previous_active_snapshot = models.JSONField(default=dict, blank=True)
    activated_snapshot = models.JSONField(default=dict, blank=True)
    activated_by = models.CharField(max_length=120, blank=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    blockers = models.JSONField(default=list, blank=True)
    linked_binding_artifact = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['activation_status', '-created_at'])]


class ActivePaperBindingRecord(TimeStampedModel):
    target_component = models.CharField(max_length=32)
    target_scope = models.CharField(max_length=24)
    active_binding_type = models.CharField(max_length=40, choices=BaselineBindingType.choices)
    active_snapshot = models.JSONField(default=dict, blank=True)
    source_activation = models.ForeignKey(
        PaperBaselineActivation,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='active_binding_records',
    )
    status = models.CharField(max_length=16, choices=ActivePaperBindingStatus.choices, default=ActivePaperBindingStatus.ACTIVE)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['target_component', 'target_scope', 'status', '-created_at'])]


class BaselineActivationRecommendation(TimeStampedModel):
    review_run = models.ForeignKey(BaselineActivationRun, on_delete=models.CASCADE, related_name='recommendations')
    target_activation = models.ForeignKey(
        PaperBaselineActivation,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='recommendations',
    )
    recommendation_type = models.CharField(max_length=48, choices=BaselineActivationRecommendationType.choices)
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    blockers = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['recommendation_type', '-created_at'])]


class BaselineHealthReadinessStatus(models.TextChoices):
    READY = 'READY', 'Ready'
    NEEDS_MORE_DATA = 'NEEDS_MORE_DATA', 'Needs more data'
    BLOCKED = 'BLOCKED', 'Blocked'


class BaselineHealthStatusCode(models.TextChoices):
    HEALTHY = 'HEALTHY', 'Healthy'
    UNDER_WATCH = 'UNDER_WATCH', 'Under watch'
    DEGRADED = 'DEGRADED', 'Degraded'
    REVIEW_REQUIRED = 'REVIEW_REQUIRED', 'Review required'
    ROLLBACK_REVIEW_RECOMMENDED = 'ROLLBACK_REVIEW_RECOMMENDED', 'Rollback review recommended'
    INSUFFICIENT_DATA = 'INSUFFICIENT_DATA', 'Insufficient data'


class BaselineHealthSignalType(models.TextChoices):
    CALIBRATION_DRIFT = 'calibration_drift', 'Calibration drift'
    RISK_PRECISION_DROP = 'risk_precision_drop', 'Risk precision drop'
    SHORTLIST_QUALITY_DROP = 'shortlist_quality_drop', 'Shortlist quality drop'
    OPPORTUNITY_CONVICTION_DROP = 'opportunity_conviction_drop', 'Opportunity conviction drop'
    PROVIDER_BIAS_REAPPEARANCE = 'provider_bias_reappearance', 'Provider bias reappearance'
    CATEGORY_BIAS_REAPPEARANCE = 'category_bias_reappearance', 'Category bias reappearance'
    WATCHLIST_NOISE_INCREASE = 'watchlist_noise_increase', 'Watchlist noise increase'
    ROLLBACK_PRESSURE = 'rollback_pressure', 'Rollback pressure'
    INSUFFICIENT_OBSERVATION = 'insufficient_observation', 'Insufficient observation'


class BaselineHealthSignalSeverity(models.TextChoices):
    LOW = 'LOW', 'Low'
    MEDIUM = 'MEDIUM', 'Medium'
    HIGH = 'HIGH', 'High'
    CRITICAL = 'CRITICAL', 'Critical'


class BaselineHealthSignalDirection(models.TextChoices):
    IMPROVING = 'improving', 'Improving'
    STABLE = 'stable', 'Stable'
    DEGRADING = 'degrading', 'Degrading'


class BaselineHealthRecommendationType(models.TextChoices):
    KEEP_BASELINE_ACTIVE = 'KEEP_BASELINE_ACTIVE', 'Keep baseline active'
    KEEP_UNDER_WATCH = 'KEEP_UNDER_WATCH', 'Keep under watch'
    REQUIRE_REEVALUATION = 'REQUIRE_REEVALUATION', 'Require re-evaluation'
    OPEN_TUNING_REVIEW = 'OPEN_TUNING_REVIEW', 'Open tuning review'
    REQUIRE_MANUAL_BASELINE_REVIEW = 'REQUIRE_MANUAL_BASELINE_REVIEW', 'Require manual baseline review'
    PREPARE_ROLLBACK_REVIEW = 'PREPARE_ROLLBACK_REVIEW', 'Prepare rollback review'
    REORDER_BASELINE_HEALTH_PRIORITY = 'REORDER_BASELINE_HEALTH_PRIORITY', 'Reorder baseline health priority'


class BaselineHealthRun(TimeStampedModel):
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    linked_baseline_activation_run = models.ForeignKey(
        BaselineActivationRun,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='baseline_health_runs',
    )
    active_binding_count = models.PositiveIntegerField(default=0)
    healthy_count = models.PositiveIntegerField(default=0)
    watch_count = models.PositiveIntegerField(default=0)
    degraded_count = models.PositiveIntegerField(default=0)
    review_required_count = models.PositiveIntegerField(default=0)
    rollback_review_count = models.PositiveIntegerField(default=0)
    recommendation_summary = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']


class BaselineHealthCandidate(TimeStampedModel):
    review_run = models.ForeignKey(BaselineHealthRun, on_delete=models.CASCADE, related_name='candidates')
    linked_active_binding = models.ForeignKey(
        ActivePaperBindingRecord, on_delete=models.CASCADE, related_name='baseline_health_candidates'
    )
    linked_baseline_activation = models.ForeignKey(
        PaperBaselineActivation,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='baseline_health_candidates',
    )
    target_component = models.CharField(max_length=32)
    target_scope = models.CharField(max_length=24)
    active_binding_type = models.CharField(max_length=40, choices=BaselineBindingType.choices)
    current_health_inputs = models.JSONField(default=dict, blank=True)
    readiness_status = models.CharField(
        max_length=20,
        choices=BaselineHealthReadinessStatus.choices,
        default=BaselineHealthReadinessStatus.NEEDS_MORE_DATA,
    )
    blockers = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['readiness_status', '-created_at'])]


class BaselineHealthStatus(TimeStampedModel):
    linked_candidate = models.ForeignKey(
        BaselineHealthCandidate, on_delete=models.CASCADE, related_name='health_statuses'
    )
    health_status = models.CharField(max_length=40, choices=BaselineHealthStatusCode.choices)
    calibration_health_score = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    risk_gate_health_score = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    opportunity_quality_health_score = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    drift_risk_score = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    regression_risk_score = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    blockers = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['health_status', '-created_at'])]


class BaselineHealthSignal(TimeStampedModel):
    linked_status = models.ForeignKey(
        BaselineHealthStatus, on_delete=models.CASCADE, related_name='signals'
    )
    signal_type = models.CharField(max_length=40, choices=BaselineHealthSignalType.choices)
    signal_severity = models.CharField(max_length=16, choices=BaselineHealthSignalSeverity.choices)
    signal_direction = models.CharField(max_length=16, choices=BaselineHealthSignalDirection.choices)
    evidence_summary = models.JSONField(default=dict, blank=True)
    rationale = models.CharField(max_length=255)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['signal_type', 'signal_severity', '-created_at'])]


class BaselineHealthRecommendation(TimeStampedModel):
    review_run = models.ForeignKey(BaselineHealthRun, on_delete=models.CASCADE, related_name='recommendations')
    target_status = models.ForeignKey(
        BaselineHealthStatus,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='recommendations',
    )
    recommendation_type = models.CharField(max_length=48, choices=BaselineHealthRecommendationType.choices)
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    blockers = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['recommendation_type', '-created_at'])]


class BaselineResponseType(models.TextChoices):
    KEEP_UNDER_WATCH = 'KEEP_UNDER_WATCH', 'Keep under watch'
    OPEN_REEVALUATION = 'OPEN_REEVALUATION', 'Open re-evaluation'
    OPEN_TUNING_REVIEW = 'OPEN_TUNING_REVIEW', 'Open tuning review'
    REQUIRE_MANUAL_BASELINE_REVIEW = 'REQUIRE_MANUAL_BASELINE_REVIEW', 'Require manual baseline review'
    PREPARE_ROLLBACK_REVIEW = 'PREPARE_ROLLBACK_REVIEW', 'Prepare rollback review'
    REQUIRE_COMMITTEE_RECHECK = 'REQUIRE_COMMITTEE_RECHECK', 'Require committee recheck'


class BaselineResponsePriority(models.TextChoices):
    LOW = 'LOW', 'Low'
    MEDIUM = 'MEDIUM', 'Medium'
    HIGH = 'HIGH', 'High'
    CRITICAL = 'CRITICAL', 'Critical'


class BaselineResponseCaseStatus(models.TextChoices):
    OPEN = 'OPEN', 'Open'
    UNDER_REVIEW = 'UNDER_REVIEW', 'Under review'
    ROUTED = 'ROUTED', 'Routed'
    DEFERRED = 'DEFERRED', 'Deferred'
    CLOSED_NO_ACTION = 'CLOSED_NO_ACTION', 'Closed with no action'
    ESCALATED = 'ESCALATED', 'Escalated'


class BaselineResponseEvidenceStatus(models.TextChoices):
    STRONG = 'STRONG', 'Strong'
    MIXED = 'MIXED', 'Mixed'
    WEAK = 'WEAK', 'Weak'
    INSUFFICIENT = 'INSUFFICIENT', 'Insufficient'


class BaselineResponseRoutingTarget(models.TextChoices):
    EVALUATION_LAB = 'evaluation_lab', 'Evaluation lab'
    TUNING_BOARD = 'tuning_board', 'Tuning board'
    PROMOTION_COMMITTEE = 'promotion_committee', 'Promotion committee'
    CERTIFICATION_BOARD = 'certification_board', 'Certification board'
    ROLLBACK_REVIEW = 'rollback_review', 'Rollback review'
    MONITORING_ONLY = 'monitoring_only', 'Monitoring only'


class BaselineResponseRoutingStatus(models.TextChoices):
    PROPOSED = 'PROPOSED', 'Proposed'
    READY = 'READY', 'Ready'
    SENT = 'SENT', 'Sent'
    DEFERRED = 'DEFERRED', 'Deferred'
    BLOCKED = 'BLOCKED', 'Blocked'


class BaselineResponseRecommendationType(models.TextChoices):
    KEEP_UNDER_WATCH = 'KEEP_UNDER_WATCH', 'Keep under watch'
    OPEN_REEVALUATION = 'OPEN_REEVALUATION', 'Open re-evaluation'
    OPEN_TUNING_REVIEW = 'OPEN_TUNING_REVIEW', 'Open tuning review'
    REQUIRE_MANUAL_BASELINE_REVIEW = 'REQUIRE_MANUAL_BASELINE_REVIEW', 'Require manual baseline review'
    PREPARE_ROLLBACK_REVIEW = 'PREPARE_ROLLBACK_REVIEW', 'Prepare rollback review'
    REQUIRE_MORE_EVIDENCE = 'REQUIRE_MORE_EVIDENCE', 'Require more evidence'
    REORDER_RESPONSE_PRIORITY = 'REORDER_RESPONSE_PRIORITY', 'Reorder response priority'


class BaselineResponseRun(TimeStampedModel):
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    linked_baseline_health_run = models.ForeignKey(
        BaselineHealthRun,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='baseline_response_runs',
    )
    candidate_count = models.PositiveIntegerField(default=0)
    opened_case_count = models.PositiveIntegerField(default=0)
    watch_case_count = models.PositiveIntegerField(default=0)
    reevaluation_case_count = models.PositiveIntegerField(default=0)
    tuning_case_count = models.PositiveIntegerField(default=0)
    rollback_review_case_count = models.PositiveIntegerField(default=0)
    recommendation_summary = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']


class BaselineResponseCase(TimeStampedModel):
    review_run = models.ForeignKey(BaselineResponseRun, on_delete=models.CASCADE, related_name='cases')
    linked_active_binding = models.ForeignKey(
        ActivePaperBindingRecord,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='baseline_response_cases',
    )
    linked_baseline_health_status = models.ForeignKey(
        BaselineHealthStatus,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='response_cases',
    )
    linked_health_signals = models.JSONField(default=list, blank=True)
    target_component = models.CharField(max_length=32)
    target_scope = models.CharField(max_length=24)
    response_type = models.CharField(max_length=48, choices=BaselineResponseType.choices)
    priority_level = models.CharField(max_length=16, choices=BaselineResponsePriority.choices, default=BaselineResponsePriority.MEDIUM)
    case_status = models.CharField(max_length=24, choices=BaselineResponseCaseStatus.choices, default=BaselineResponseCaseStatus.OPEN)
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    blockers = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['response_type', 'priority_level', 'case_status', '-created_at'])]


class ResponseEvidencePack(TimeStampedModel):
    linked_response_case = models.OneToOneField(
        BaselineResponseCase,
        on_delete=models.CASCADE,
        related_name='evidence_pack',
    )
    summary = models.CharField(max_length=255)
    linked_health_status = models.ForeignKey(
        BaselineHealthStatus,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='response_evidence_packs',
    )
    linked_health_signals = models.JSONField(default=list, blank=True)
    linked_evaluation_metrics = models.JSONField(default=dict, blank=True)
    linked_risk_context = models.JSONField(default=dict, blank=True)
    linked_opportunity_context = models.JSONField(default=dict, blank=True)
    confidence_score = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    severity_score = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    urgency_score = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    evidence_status = models.CharField(
        max_length=16,
        choices=BaselineResponseEvidenceStatus.choices,
        default=BaselineResponseEvidenceStatus.INSUFFICIENT,
    )
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['evidence_status', '-created_at'])]


class ResponseRoutingDecision(TimeStampedModel):
    linked_response_case = models.OneToOneField(
        BaselineResponseCase,
        on_delete=models.CASCADE,
        related_name='routing_decision',
    )
    routing_target = models.CharField(max_length=32, choices=BaselineResponseRoutingTarget.choices)
    routing_status = models.CharField(max_length=16, choices=BaselineResponseRoutingStatus.choices, default=BaselineResponseRoutingStatus.PROPOSED)
    routing_rationale = models.CharField(max_length=255)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['routing_target', 'routing_status', '-created_at'])]


class BaselineResponseRecommendation(TimeStampedModel):
    review_run = models.ForeignKey(BaselineResponseRun, on_delete=models.CASCADE, related_name='recommendations')
    target_case = models.ForeignKey(
        BaselineResponseCase,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='recommendations',
    )
    recommendation_type = models.CharField(max_length=48, choices=BaselineResponseRecommendationType.choices)
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    blockers = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['recommendation_type', '-created_at'])]

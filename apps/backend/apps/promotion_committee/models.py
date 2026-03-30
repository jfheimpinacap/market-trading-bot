from django.db import models

from apps.common.models import TimeStampedModel
from apps.readiness_lab.models import ReadinessStatus


class PromotionReviewRunStatus(models.TextChoices):
    COMPLETED = 'COMPLETED', 'Completed'
    FAILED = 'FAILED', 'Failed'


class PromotionRecommendationCode(models.TextChoices):
    KEEP_CURRENT_CHAMPION = 'KEEP_CURRENT_CHAMPION', 'Keep current champion'
    PROMOTE_CHALLENGER = 'PROMOTE_CHALLENGER', 'Promote challenger'
    EXTEND_SHADOW_TEST = 'EXTEND_SHADOW_TEST', 'Extend shadow test'
    REVERT_TO_CONSERVATIVE_STACK = 'REVERT_TO_CONSERVATIVE_STACK', 'Revert to conservative stack'
    MANUAL_REVIEW_REQUIRED = 'MANUAL_REVIEW_REQUIRED', 'Manual review required'


class PromotionDecisionMode(models.TextChoices):
    RECOMMENDATION_ONLY = 'RECOMMENDATION_ONLY', 'Recommendation only'
    MANUAL_APPLY = 'MANUAL_APPLY', 'Manual apply'


class PromotionTargetComponent(models.TextChoices):
    PREDICTION = 'prediction', 'Prediction'
    RISK = 'risk', 'Risk'
    RESEARCH = 'research', 'Research'
    OPPORTUNITY_CYCLE = 'opportunity_cycle', 'Opportunity cycle'
    CALIBRATION = 'calibration', 'Calibration'
    LEARNING = 'learning', 'Learning'


class PromotionTargetScope(models.TextChoices):
    GLOBAL = 'global', 'Global'
    PROVIDER = 'provider', 'Provider'
    CATEGORY = 'category', 'Category'
    HORIZON_BAND = 'horizon_band', 'Horizon band'
    MODEL_MODE = 'model_mode', 'Model mode'
    SOURCE_TYPE = 'source_type', 'Source type'


class PromotionChangeType(models.TextChoices):
    THRESHOLD_UPDATE = 'threshold_update', 'Threshold update'
    CALIBRATION_UPDATE = 'calibration_update', 'Calibration update'
    RISK_GATE_UPDATE = 'risk_gate_update', 'Risk gate update'
    SIZE_CAP_UPDATE = 'size_cap_update', 'Size cap update'
    SHORTLIST_UPDATE = 'shortlist_update', 'Shortlist update'
    CONVICTION_UPDATE = 'conviction_update', 'Conviction update'
    CAUTION_WEIGHT_UPDATE = 'caution_weight_update', 'Caution weight update'
    REVIEW_RULE_UPDATE = 'review_rule_update', 'Review rule update'


class PromotionCaseStatus(models.TextChoices):
    PROPOSED = 'PROPOSED', 'Proposed'
    READY_FOR_REVIEW = 'READY_FOR_REVIEW', 'Ready for review'
    NEEDS_MORE_DATA = 'NEEDS_MORE_DATA', 'Needs more data'
    DEFERRED = 'DEFERRED', 'Deferred'
    REJECTED = 'REJECTED', 'Rejected'
    APPROVED_FOR_MANUAL_ADOPTION = 'APPROVED_FOR_MANUAL_ADOPTION', 'Approved for manual adoption'


class PromotionPriorityLevel(models.TextChoices):
    LOW = 'LOW', 'Low'
    MEDIUM = 'MEDIUM', 'Medium'
    HIGH = 'HIGH', 'High'
    CRITICAL = 'CRITICAL', 'Critical'


class PromotionEvidenceStatus(models.TextChoices):
    STRONG = 'STRONG', 'Strong'
    MIXED = 'MIXED', 'Mixed'
    WEAK = 'WEAK', 'Weak'
    INSUFFICIENT = 'INSUFFICIENT', 'Insufficient'


class PromotionDecisionRecommendationType(models.TextChoices):
    APPROVE_FOR_MANUAL_ADOPTION = 'APPROVE_FOR_MANUAL_ADOPTION', 'Approve for manual adoption'
    DEFER_FOR_MORE_EVIDENCE = 'DEFER_FOR_MORE_EVIDENCE', 'Defer for more evidence'
    REJECT_CHANGE = 'REJECT_CHANGE', 'Reject change'
    REQUIRE_COMMITTEE_REVIEW = 'REQUIRE_COMMITTEE_REVIEW', 'Require committee review'
    SPLIT_SCOPE_AND_RETEST = 'SPLIT_SCOPE_AND_RETEST', 'Split scope and retest'
    GROUP_WITH_RELATED_CHANGES = 'GROUP_WITH_RELATED_CHANGES', 'Group with related changes'
    REORDER_PROMOTION_PRIORITY = 'REORDER_PROMOTION_PRIORITY', 'Reorder promotion priority'


class StackEvidenceSnapshot(TimeStampedModel):
    champion_binding = models.ForeignKey(
        'champion_challenger.StackProfileBinding', on_delete=models.PROTECT, related_name='promotion_champion_evidence'
    )
    challenger_binding = models.ForeignKey(
        'champion_challenger.StackProfileBinding',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='promotion_challenger_evidence',
    )
    champion_challenger_summary = models.JSONField(default=dict, blank=True)
    execution_aware_metrics = models.JSONField(default=dict, blank=True)
    readiness_summary = models.JSONField(default=dict, blank=True)
    profile_governance_context = models.JSONField(default=dict, blank=True)
    portfolio_governor_context = models.JSONField(default=dict, blank=True)
    model_governance_summary = models.JSONField(default=dict, blank=True)
    precedent_warnings = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class PromotionReviewRun(TimeStampedModel):
    status = models.CharField(max_length=16, choices=PromotionReviewRunStatus.choices, default=PromotionReviewRunStatus.COMPLETED)
    decision_mode = models.CharField(
        max_length=24, choices=PromotionDecisionMode.choices, default=PromotionDecisionMode.RECOMMENDATION_ONLY
    )
    readiness_status = models.CharField(max_length=24, choices=ReadinessStatus.choices, blank=True)
    evidence_snapshot = models.ForeignKey(
        StackEvidenceSnapshot, on_delete=models.PROTECT, related_name='promotion_review_runs'
    )
    recommendation_code = models.CharField(max_length=40, choices=PromotionRecommendationCode.choices)
    confidence = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    rationale = models.TextField(blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    blocking_constraints = models.JSONField(default=list, blank=True)
    evidence_summary = models.JSONField(default=dict, blank=True)
    summary = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class PromotionDecisionLog(TimeStampedModel):
    review_run = models.ForeignKey(PromotionReviewRun, on_delete=models.CASCADE, related_name='decision_logs')
    event_type = models.CharField(max_length=32, default='RECOMMENDATION_ISSUED')
    actor = models.CharField(max_length=64, default='system')
    notes = models.TextField(blank=True)
    payload = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class PromotionReviewCycleRun(TimeStampedModel):
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    linked_experiment_run = models.ForeignKey(
        'experiment_lab.TuningExperimentRun',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='promotion_review_runs',
    )
    candidate_count = models.PositiveIntegerField(default=0)
    ready_for_review_count = models.PositiveIntegerField(default=0)
    needs_more_data_count = models.PositiveIntegerField(default=0)
    deferred_count = models.PositiveIntegerField(default=0)
    rejected_count = models.PositiveIntegerField(default=0)
    high_priority_count = models.PositiveIntegerField(default=0)
    recommendation_summary = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']


class PromotionCase(TimeStampedModel):
    review_run = models.ForeignKey(PromotionReviewCycleRun, on_delete=models.CASCADE, related_name='cases')
    linked_experiment_candidate = models.ForeignKey(
        'experiment_lab.ExperimentCandidate', null=True, blank=True, on_delete=models.SET_NULL, related_name='promotion_cases'
    )
    linked_comparison = models.ForeignKey(
        'experiment_lab.TuningChampionChallengerComparison', null=True, blank=True, on_delete=models.SET_NULL, related_name='promotion_cases'
    )
    linked_tuning_proposal = models.ForeignKey(
        'tuning_board.TuningProposal', null=True, blank=True, on_delete=models.SET_NULL, related_name='promotion_cases'
    )
    linked_bundle = models.ForeignKey(
        'tuning_board.TuningProposalBundle', null=True, blank=True, on_delete=models.SET_NULL, related_name='promotion_cases'
    )
    target_component = models.CharField(max_length=32, choices=PromotionTargetComponent.choices)
    target_scope = models.CharField(max_length=24, choices=PromotionTargetScope.choices)
    change_type = models.CharField(max_length=32, choices=PromotionChangeType.choices)
    case_status = models.CharField(max_length=40, choices=PromotionCaseStatus.choices, default=PromotionCaseStatus.PROPOSED)
    priority_level = models.CharField(max_length=16, choices=PromotionPriorityLevel.choices, default=PromotionPriorityLevel.MEDIUM)
    current_value = models.CharField(max_length=128, blank=True)
    proposed_value = models.CharField(max_length=128, blank=True)
    rationale = models.CharField(max_length=255)
    blockers = models.JSONField(default=list, blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['case_status', '-created_at']), models.Index(fields=['priority_level', '-created_at'])]


class PromotionEvidencePack(TimeStampedModel):
    linked_promotion_case = models.ForeignKey(PromotionCase, on_delete=models.CASCADE, related_name='evidence_packs')
    summary = models.CharField(max_length=255)
    linked_metrics = models.JSONField(default=dict, blank=True)
    linked_comparisons = models.JSONField(default=dict, blank=True)
    linked_recommendations = models.JSONField(default=dict, blank=True)
    sample_count = models.PositiveIntegerField(default=0)
    confidence_score = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    risk_of_adoption_score = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    expected_benefit_score = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    evidence_status = models.CharField(max_length=16, choices=PromotionEvidenceStatus.choices, default=PromotionEvidenceStatus.INSUFFICIENT)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['evidence_status', '-created_at'])]


class PromotionDecisionRecommendation(TimeStampedModel):
    review_run = models.ForeignKey(PromotionReviewCycleRun, on_delete=models.CASCADE, related_name='decision_recommendations')
    target_case = models.ForeignKey(PromotionCase, null=True, blank=True, on_delete=models.SET_NULL, related_name='decision_recommendations')
    recommendation_type = models.CharField(max_length=40, choices=PromotionDecisionRecommendationType.choices)
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    blockers = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['recommendation_type', '-created_at'])]


class AdoptionTargetResolutionStatus(models.TextChoices):
    RESOLVED = 'RESOLVED', 'Resolved'
    PARTIAL = 'PARTIAL', 'Partial'
    BLOCKED = 'BLOCKED', 'Blocked'
    UNKNOWN = 'UNKNOWN', 'Unknown'


class ManualAdoptionActionType(models.TextChoices):
    APPLY_POLICY_TUNING_CHANGE = 'APPLY_POLICY_TUNING_CHANGE', 'Apply policy tuning change'
    APPLY_TRUST_CALIBRATION_CHANGE = 'APPLY_TRUST_CALIBRATION_CHANGE', 'Apply trust calibration change'
    APPLY_STACK_BINDING_CHANGE = 'APPLY_STACK_BINDING_CHANGE', 'Apply stack binding change'
    PREPARE_ROLLOUT_PLAN = 'PREPARE_ROLLOUT_PLAN', 'Prepare rollout plan'
    RECORD_MANUAL_ADOPTION = 'RECORD_MANUAL_ADOPTION', 'Record manual adoption'
    REQUIRE_TARGET_MAPPING = 'REQUIRE_TARGET_MAPPING', 'Require target mapping'


class ManualAdoptionActionStatus(models.TextChoices):
    PROPOSED = 'PROPOSED', 'Proposed'
    READY_TO_APPLY = 'READY_TO_APPLY', 'Ready to apply'
    APPLIED = 'APPLIED', 'Applied'
    BLOCKED = 'BLOCKED', 'Blocked'
    DEFERRED = 'DEFERRED', 'Deferred'
    ROLLBACK_AVAILABLE = 'ROLLBACK_AVAILABLE', 'Rollback available'


class AdoptionRollbackType(models.TextChoices):
    REVERT_VALUE = 'REVERT_VALUE', 'Revert value'
    RESTORE_BINDING = 'RESTORE_BINDING', 'Restore binding'
    CANCEL_ROLLOUT_PLAN = 'CANCEL_ROLLOUT_PLAN', 'Cancel rollout plan'
    RETURN_TO_BASELINE = 'RETURN_TO_BASELINE', 'Return to baseline'


class AdoptionRollbackStatus(models.TextChoices):
    PREPARED = 'PREPARED', 'Prepared'
    AVAILABLE = 'AVAILABLE', 'Available'
    EXECUTED = 'EXECUTED', 'Executed'
    NOT_NEEDED = 'NOT_NEEDED', 'Not needed'


class AdoptionActionRecommendationType(models.TextChoices):
    APPLY_CHANGE_MANUALLY = 'APPLY_CHANGE_MANUALLY', 'Apply change manually'
    PREPARE_ROLLOUT_PLAN = 'PREPARE_ROLLOUT_PLAN', 'Prepare rollout plan'
    REQUIRE_TARGET_MAPPING = 'REQUIRE_TARGET_MAPPING', 'Require target mapping'
    DEFER_ADOPTION = 'DEFER_ADOPTION', 'Defer adoption'
    PREPARE_ROLLBACK = 'PREPARE_ROLLBACK', 'Prepare rollback'
    REQUIRE_COMMITTEE_RECHECK = 'REQUIRE_COMMITTEE_RECHECK', 'Require committee recheck'
    REORDER_ADOPTION_PRIORITY = 'REORDER_ADOPTION_PRIORITY', 'Reorder adoption priority'


class RolloutNeedLevel(models.TextChoices):
    DIRECT_APPLY_OK = 'DIRECT_APPLY_OK', 'Direct apply ok'
    ROLLOUT_RECOMMENDED = 'ROLLOUT_RECOMMENDED', 'Rollout recommended'
    ROLLOUT_REQUIRED = 'ROLLOUT_REQUIRED', 'Rollout required'


class RolloutPlanType(models.TextChoices):
    DIRECT_CONFIG_APPLY = 'DIRECT_CONFIG_APPLY', 'Direct config apply'
    STAGED_BINDING_ROLLOUT = 'STAGED_BINDING_ROLLOUT', 'Staged binding rollout'
    SHADOW_CONFIG_ROLLOUT = 'SHADOW_CONFIG_ROLLOUT', 'Shadow config rollout'
    TRUST_CALIBRATION_ROLLOUT = 'TRUST_CALIBRATION_ROLLOUT', 'Trust calibration rollout'
    POLICY_TUNING_ROLLOUT = 'POLICY_TUNING_ROLLOUT', 'Policy tuning rollout'


class ManualRolloutPlanStatus(models.TextChoices):
    PROPOSED = 'PROPOSED', 'Proposed'
    READY = 'READY', 'Ready'
    EXECUTED = 'EXECUTED', 'Executed'
    BLOCKED = 'BLOCKED', 'Blocked'
    DEFERRED = 'DEFERRED', 'Deferred'
    ROLLBACK_AVAILABLE = 'ROLLBACK_AVAILABLE', 'Rollback available'


class RolloutCheckpointType(models.TextChoices):
    PRE_APPLY_CHECK = 'pre_apply_check', 'Pre apply check'
    POST_APPLY_CHECK = 'post_apply_check', 'Post apply check'
    METRIC_DRIFT_CHECK = 'metric_drift_check', 'Metric drift check'
    CALIBRATION_CHECK = 'calibration_check', 'Calibration check'
    RISK_GATE_CHECK = 'risk_gate_check', 'Risk gate check'
    PROPOSAL_QUALITY_CHECK = 'proposal_quality_check', 'Proposal quality check'
    ROLLBACK_READINESS_CHECK = 'rollback_readiness_check', 'Rollback readiness check'


class RolloutCheckpointStatus(models.TextChoices):
    PLANNED = 'PLANNED', 'Planned'
    PASSED = 'PASSED', 'Passed'
    FAILED = 'FAILED', 'Failed'
    SKIPPED = 'SKIPPED', 'Skipped'


class ManualRollbackExecutionStatus(models.TextChoices):
    READY = 'READY', 'Ready'
    EXECUTED = 'EXECUTED', 'Executed'
    BLOCKED = 'BLOCKED', 'Blocked'
    NOT_NEEDED = 'NOT_NEEDED', 'Not needed'


class RolloutPreparationRecommendationType(models.TextChoices):
    PREPARE_MANUAL_ROLLOUT = 'PREPARE_MANUAL_ROLLOUT', 'Prepare manual rollout'
    DIRECT_APPLY_OK = 'DIRECT_APPLY_OK', 'Direct apply ok'
    REQUIRE_ROLLOUT_CHECKPOINTS = 'REQUIRE_ROLLOUT_CHECKPOINTS', 'Require rollout checkpoints'
    ROLLBACK_READY = 'ROLLBACK_READY', 'Rollback ready'
    EXECUTE_ROLLBACK_MANUALLY = 'EXECUTE_ROLLBACK_MANUALLY', 'Execute rollback manually'
    REQUIRE_TARGET_RECHECK = 'REQUIRE_TARGET_RECHECK', 'Require target recheck'
    DEFER_ROLLOUT = 'DEFER_ROLLOUT', 'Defer rollout'
    REORDER_ROLLOUT_PRIORITY = 'REORDER_ROLLOUT_PRIORITY', 'Reorder rollout priority'


class PromotionAdoptionRun(TimeStampedModel):
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    linked_promotion_review_run = models.ForeignKey(
        PromotionReviewCycleRun,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='adoption_runs',
    )
    candidate_count = models.PositiveIntegerField(default=0)
    ready_to_apply_count = models.PositiveIntegerField(default=0)
    blocked_count = models.PositiveIntegerField(default=0)
    applied_count = models.PositiveIntegerField(default=0)
    rollback_plan_count = models.PositiveIntegerField(default=0)
    rollout_handoff_count = models.PositiveIntegerField(default=0)
    recommendation_summary = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']


class AdoptionActionCandidate(TimeStampedModel):
    linked_promotion_case = models.OneToOneField(PromotionCase, on_delete=models.CASCADE, related_name='adoption_candidate')
    adoption_run = models.ForeignKey(PromotionAdoptionRun, on_delete=models.CASCADE, related_name='candidates')
    target_component = models.CharField(max_length=32, choices=PromotionTargetComponent.choices)
    target_scope = models.CharField(max_length=24, choices=PromotionTargetScope.choices)
    change_type = models.CharField(max_length=32, choices=PromotionChangeType.choices)
    current_value = models.CharField(max_length=128, blank=True)
    proposed_value = models.CharField(max_length=128, blank=True)
    target_resolution_status = models.CharField(
        max_length=16, choices=AdoptionTargetResolutionStatus.choices, default=AdoptionTargetResolutionStatus.UNKNOWN
    )
    ready_for_action = models.BooleanField(default=False)
    blockers = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['target_resolution_status', '-created_at'])]


class ManualAdoptionAction(TimeStampedModel):
    linked_promotion_case = models.ForeignKey(PromotionCase, on_delete=models.CASCADE, related_name='adoption_actions')
    linked_candidate = models.ForeignKey(AdoptionActionCandidate, on_delete=models.CASCADE, related_name='actions')
    adoption_run = models.ForeignKey(PromotionAdoptionRun, on_delete=models.CASCADE, related_name='actions')
    action_type = models.CharField(max_length=40, choices=ManualAdoptionActionType.choices)
    action_status = models.CharField(max_length=24, choices=ManualAdoptionActionStatus.choices, default=ManualAdoptionActionStatus.PROPOSED)
    target_component = models.CharField(max_length=32, choices=PromotionTargetComponent.choices)
    target_scope = models.CharField(max_length=24, choices=PromotionTargetScope.choices)
    current_value_snapshot = models.JSONField(default=dict, blank=True)
    proposed_value_snapshot = models.JSONField(default=dict, blank=True)
    applied_by = models.CharField(max_length=64, blank=True)
    applied_at = models.DateTimeField(null=True, blank=True)
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    blockers = models.JSONField(default=list, blank=True)
    linked_target_artifact = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['action_status', '-created_at'])]


class AdoptionRollbackPlan(TimeStampedModel):
    linked_manual_action = models.OneToOneField(ManualAdoptionAction, on_delete=models.CASCADE, related_name='rollback_plan')
    rollback_type = models.CharField(max_length=32, choices=AdoptionRollbackType.choices)
    rollback_status = models.CharField(max_length=16, choices=AdoptionRollbackStatus.choices, default=AdoptionRollbackStatus.PREPARED)
    rollback_target_snapshot = models.JSONField(default=dict, blank=True)
    rationale = models.CharField(max_length=255)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class AdoptionActionRecommendation(TimeStampedModel):
    adoption_run = models.ForeignKey(PromotionAdoptionRun, on_delete=models.CASCADE, related_name='adoption_recommendations')
    linked_promotion_case = models.ForeignKey(
        PromotionCase, null=True, blank=True, on_delete=models.SET_NULL, related_name='adoption_recommendations'
    )
    target_action = models.ForeignKey(
        ManualAdoptionAction, null=True, blank=True, on_delete=models.SET_NULL, related_name='recommendations'
    )
    recommendation_type = models.CharField(max_length=40, choices=AdoptionActionRecommendationType.choices)
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    blockers = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class RolloutPreparationRun(TimeStampedModel):
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    linked_adoption_run = models.ForeignKey(
        PromotionAdoptionRun, null=True, blank=True, on_delete=models.SET_NULL, related_name='rollout_preparation_runs'
    )
    candidate_count = models.PositiveIntegerField(default=0)
    rollout_ready_count = models.PositiveIntegerField(default=0)
    blocked_count = models.PositiveIntegerField(default=0)
    checkpoint_count = models.PositiveIntegerField(default=0)
    rollback_ready_count = models.PositiveIntegerField(default=0)
    rollback_executed_count = models.PositiveIntegerField(default=0)
    recommendation_summary = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']


class RolloutActionCandidate(TimeStampedModel):
    preparation_run = models.ForeignKey(RolloutPreparationRun, on_delete=models.CASCADE, related_name='candidates')
    linked_manual_adoption_action = models.OneToOneField(
        ManualAdoptionAction, on_delete=models.CASCADE, related_name='rollout_candidate'
    )
    linked_promotion_case = models.ForeignKey(PromotionCase, on_delete=models.CASCADE, related_name='rollout_candidates')
    target_component = models.CharField(max_length=32, choices=PromotionTargetComponent.choices)
    target_scope = models.CharField(max_length=24, choices=PromotionTargetScope.choices)
    action_type = models.CharField(max_length=40, choices=ManualAdoptionActionType.choices)
    current_value_snapshot = models.JSONField(default=dict, blank=True)
    proposed_value_snapshot = models.JSONField(default=dict, blank=True)
    rollout_need_level = models.CharField(max_length=24, choices=RolloutNeedLevel.choices, default=RolloutNeedLevel.ROLLOUT_RECOMMENDED)
    target_resolution_status = models.CharField(
        max_length=16, choices=AdoptionTargetResolutionStatus.choices, default=AdoptionTargetResolutionStatus.UNKNOWN
    )
    ready_for_rollout = models.BooleanField(default=False)
    blockers = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class ManualRolloutPlan(TimeStampedModel):
    linked_candidate = models.ForeignKey(RolloutActionCandidate, on_delete=models.CASCADE, related_name='rollout_plans')
    linked_manual_adoption_action = models.ForeignKey(
        ManualAdoptionAction, on_delete=models.CASCADE, related_name='rollout_plans'
    )
    rollout_plan_type = models.CharField(max_length=36, choices=RolloutPlanType.choices, default=RolloutPlanType.DIRECT_CONFIG_APPLY)
    rollout_status = models.CharField(max_length=20, choices=ManualRolloutPlanStatus.choices, default=ManualRolloutPlanStatus.PROPOSED)
    target_component = models.CharField(max_length=32, choices=PromotionTargetComponent.choices)
    target_scope = models.CharField(max_length=24, choices=PromotionTargetScope.choices)
    rollout_rationale = models.CharField(max_length=255)
    staged_steps = models.JSONField(default=list, blank=True)
    monitoring_intent = models.JSONField(default=dict, blank=True)
    linked_rollout_artifact = models.CharField(max_length=255, blank=True)
    executed_by = models.CharField(max_length=64, blank=True)
    executed_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class RolloutCheckpointPlan(TimeStampedModel):
    linked_rollout_plan = models.ForeignKey(ManualRolloutPlan, on_delete=models.CASCADE, related_name='checkpoint_plans')
    checkpoint_type = models.CharField(max_length=32, choices=RolloutCheckpointType.choices)
    checkpoint_status = models.CharField(max_length=16, choices=RolloutCheckpointStatus.choices, default=RolloutCheckpointStatus.PLANNED)
    checkpoint_rationale = models.CharField(max_length=255)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class ManualRollbackExecution(TimeStampedModel):
    linked_rollout_plan = models.ForeignKey(
        ManualRolloutPlan, null=True, blank=True, on_delete=models.SET_NULL, related_name='rollback_executions'
    )
    linked_rollback_plan = models.ForeignKey(
        AdoptionRollbackPlan, null=True, blank=True, on_delete=models.SET_NULL, related_name='manual_executions'
    )
    linked_manual_action = models.ForeignKey(ManualAdoptionAction, on_delete=models.CASCADE, related_name='rollback_executions')
    execution_status = models.CharField(
        max_length=16, choices=ManualRollbackExecutionStatus.choices, default=ManualRollbackExecutionStatus.READY
    )
    rollback_type = models.CharField(max_length=32, choices=AdoptionRollbackType.choices)
    rollback_target_snapshot = models.JSONField(default=dict, blank=True)
    executed_by = models.CharField(max_length=64, blank=True)
    executed_at = models.DateTimeField(null=True, blank=True)
    rationale = models.CharField(max_length=255)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class RolloutPreparationRecommendation(TimeStampedModel):
    preparation_run = models.ForeignKey(
        RolloutPreparationRun, on_delete=models.CASCADE, related_name='rollout_recommendations'
    )
    target_candidate = models.ForeignKey(
        RolloutActionCandidate, null=True, blank=True, on_delete=models.SET_NULL, related_name='recommendations'
    )
    target_plan = models.ForeignKey(
        ManualRolloutPlan, null=True, blank=True, on_delete=models.SET_NULL, related_name='recommendations'
    )
    recommendation_type = models.CharField(max_length=36, choices=RolloutPreparationRecommendationType.choices)
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    blockers = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']

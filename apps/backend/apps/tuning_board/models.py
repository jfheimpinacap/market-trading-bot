from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel


class TuningProposalType(models.TextChoices):
    PREDICTION_CONFIDENCE_THRESHOLD = 'prediction_confidence_threshold', 'Prediction confidence threshold'
    PREDICTION_EDGE_THRESHOLD = 'prediction_edge_threshold', 'Prediction edge threshold'
    CALIBRATION_BIAS_OFFSET = 'calibration_bias_offset', 'Calibration bias offset'
    RISK_GATE_THRESHOLD = 'risk_gate_threshold', 'Risk gate threshold'
    RISK_SIZE_CAP = 'risk_size_cap', 'Risk size cap'
    LIQUIDITY_FLOOR = 'liquidity_floor', 'Liquidity floor'
    SHORTLIST_THRESHOLD = 'shortlist_threshold', 'Shortlist threshold'
    OPPORTUNITY_CONVICTION_FLOOR = 'opportunity_conviction_floor', 'Opportunity conviction floor'
    LEARNING_CAUTION_WEIGHT = 'learning_caution_weight', 'Learning caution weight'
    MANUAL_REVIEW_RULE = 'manual_review_rule', 'Manual review rule'


class TuningScope(models.TextChoices):
    GLOBAL = 'global', 'Global'
    PROVIDER = 'provider', 'Provider'
    CATEGORY = 'category', 'Category'
    HORIZON_BAND = 'horizon_band', 'Horizon band'
    MODEL_MODE = 'model_mode', 'Model mode'
    SOURCE_TYPE = 'source_type', 'Source type'


class TuningComponent(models.TextChoices):
    RESEARCH = 'research', 'Research'
    PREDICTION = 'prediction', 'Prediction'
    RISK = 'risk', 'Risk'
    OPPORTUNITY_CYCLE = 'opportunity_cycle', 'Opportunity cycle'
    LEARNING = 'learning', 'Learning'
    CALIBRATION = 'calibration', 'Calibration'


class TuningProposalStatus(models.TextChoices):
    PROPOSED = 'PROPOSED', 'Proposed'
    WATCH = 'WATCH', 'Watch'
    READY_FOR_REVIEW = 'READY_FOR_REVIEW', 'Ready for review'
    DEFERRED = 'DEFERRED', 'Deferred'
    REJECTED = 'REJECTED', 'Rejected'
    EXPIRED = 'EXPIRED', 'Expired'


class TuningPriorityLevel(models.TextChoices):
    LOW = 'LOW', 'Low'
    MEDIUM = 'MEDIUM', 'Medium'
    HIGH = 'HIGH', 'High'
    CRITICAL = 'CRITICAL', 'Critical'


class TuningRecommendationType(models.TextChoices):
    REVIEW_PREDICTION_THRESHOLD = 'REVIEW_PREDICTION_THRESHOLD', 'Review prediction threshold'
    REVIEW_CALIBRATION_OFFSET = 'REVIEW_CALIBRATION_OFFSET', 'Review calibration offset'
    REVIEW_RISK_GATE = 'REVIEW_RISK_GATE', 'Review risk gate'
    REVIEW_SIZE_CAP = 'REVIEW_SIZE_CAP', 'Review size cap'
    REVIEW_SHORTLIST_THRESHOLD = 'REVIEW_SHORTLIST_THRESHOLD', 'Review shortlist threshold'
    REQUIRE_MORE_DATA = 'REQUIRE_MORE_DATA', 'Require more data'
    DEFER_TUNING_CHANGE = 'DEFER_TUNING_CHANGE', 'Defer tuning change'
    GROUP_IN_BUNDLE = 'GROUP_IN_BUNDLE', 'Group in bundle'
    REORDER_TUNING_PRIORITY = 'REORDER_TUNING_PRIORITY', 'Reorder tuning priority'


class TuningHypothesisType(models.TextChoices):
    IMPROVE_CALIBRATION = 'improve_calibration', 'Improve calibration'
    REDUCE_OVERCONFIDENCE = 'reduce_overconfidence', 'Reduce overconfidence'
    REDUCE_FALSE_POSITIVES = 'reduce_false_positives', 'Reduce false positives'
    REDUCE_FALSE_NEGATIVES = 'reduce_false_negatives', 'Reduce false negatives'
    TIGHTEN_RISK_GATE = 'tighten_risk_gate', 'Tighten risk gate'
    RELAX_RISK_GATE = 'relax_risk_gate', 'Relax risk gate'
    REDUCE_PROVIDER_BIAS = 'reduce_provider_bias', 'Reduce provider bias'
    REDUCE_CATEGORY_BIAS = 'reduce_category_bias', 'Reduce category bias'
    IMPROVE_WATCH_PRECISION = 'improve_watch_precision', 'Improve watch precision'


class TuningExpectedDirection(models.TextChoices):
    INCREASE = 'increase', 'Increase'
    DECREASE = 'decrease', 'Decrease'
    STABILIZE = 'stabilize', 'Stabilize'


class TuningBundleStatus(models.TextChoices):
    PROPOSED = 'PROPOSED', 'Proposed'
    READY_FOR_REVIEW = 'READY_FOR_REVIEW', 'Ready for review'
    NEEDS_MORE_DATA = 'NEEDS_MORE_DATA', 'Needs more data'
    DEFERRED = 'DEFERRED', 'Deferred'


class TuningReviewRun(TimeStampedModel):
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    linked_evaluation_run = models.ForeignKey(
        'evaluation_lab.EvaluationRuntimeRun',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='tuning_review_runs',
    )
    metrics_reviewed_count = models.PositiveIntegerField(default=0)
    poor_metric_count = models.PositiveIntegerField(default=0)
    drift_flag_count = models.PositiveIntegerField(default=0)
    proposal_count = models.PositiveIntegerField(default=0)
    high_priority_proposal_count = models.PositiveIntegerField(default=0)
    recommendation_summary = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']


class TuningProposal(TimeStampedModel):
    run = models.ForeignKey(TuningReviewRun, on_delete=models.CASCADE, related_name='proposals')
    source_metric = models.ForeignKey(
        'evaluation_lab.EffectivenessMetric', null=True, blank=True, on_delete=models.SET_NULL, related_name='tuning_proposals'
    )
    source_recommendation = models.ForeignKey(
        'evaluation_lab.EvaluationRecommendation', null=True, blank=True, on_delete=models.SET_NULL, related_name='tuning_proposals'
    )
    policy_tuning_candidate = models.ForeignKey(
        'policy_tuning.PolicyTuningCandidate', null=True, blank=True, on_delete=models.SET_NULL, related_name='governed_tuning_proposals'
    )
    proposal_type = models.CharField(max_length=64, choices=TuningProposalType.choices)
    target_scope = models.CharField(max_length=24, choices=TuningScope.choices, default=TuningScope.GLOBAL)
    target_component = models.CharField(max_length=24, choices=TuningComponent.choices)
    target_value = models.CharField(max_length=120, blank=True)
    current_value = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    proposed_value = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    proposal_status = models.CharField(max_length=24, choices=TuningProposalStatus.choices, default=TuningProposalStatus.PROPOSED)
    evidence_strength_score = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    priority_level = models.CharField(max_length=16, choices=TuningPriorityLevel.choices, default=TuningPriorityLevel.LOW)
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    blockers = models.JSONField(default=list, blank=True)
    linked_metrics = models.JSONField(default=list, blank=True)
    linked_recommendations = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['proposal_status', '-created_at']), models.Index(fields=['priority_level', '-created_at'])]


class TuningImpactHypothesis(TimeStampedModel):
    proposal = models.ForeignKey(TuningProposal, on_delete=models.CASCADE, related_name='hypotheses')
    hypothesis_type = models.CharField(max_length=48, choices=TuningHypothesisType.choices)
    expected_direction = models.CharField(max_length=16, choices=TuningExpectedDirection.choices)
    target_metric_type = models.CharField(max_length=64)
    expected_effect_size = models.DecimalField(max_digits=7, decimal_places=4, null=True, blank=True)
    rationale = models.CharField(max_length=255)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class TuningRecommendation(TimeStampedModel):
    run = models.ForeignKey(TuningReviewRun, on_delete=models.CASCADE, related_name='recommendations')
    target_proposal = models.ForeignKey(TuningProposal, null=True, blank=True, on_delete=models.SET_NULL, related_name='recommendations')
    recommendation_type = models.CharField(max_length=48, choices=TuningRecommendationType.choices)
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    blockers = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class TuningProposalBundle(TimeStampedModel):
    run = models.ForeignKey(TuningReviewRun, on_delete=models.CASCADE, related_name='bundles')
    bundle_label = models.CharField(max_length=120)
    bundle_scope = models.CharField(max_length=120)
    linked_proposals = models.ManyToManyField(TuningProposal, related_name='bundles', blank=True)
    bundle_status = models.CharField(max_length=24, choices=TuningBundleStatus.choices, default=TuningBundleStatus.PROPOSED)
    rationale = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']

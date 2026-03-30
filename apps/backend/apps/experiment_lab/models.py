from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel
from apps.continuous_demo.models import ContinuousDemoSession
from apps.evaluation_lab.models import EvaluationRun
from apps.replay_lab.models import ReplayRun


class StrategyProfileType(models.TextChoices):
    CONSERVATIVE = 'conservative', 'Conservative'
    BALANCED = 'balanced', 'Balanced'
    AGGRESSIVE = 'aggressive', 'Aggressive'
    CUSTOM = 'custom', 'Custom'


class StrategyMarketScope(models.TextChoices):
    DEMO_ONLY = 'demo_only', 'Demo only'
    REAL_ONLY = 'real_only', 'Real only'
    MIXED = 'mixed', 'Mixed'


class ExperimentRunType(models.TextChoices):
    REPLAY = 'replay', 'Replay'
    LIVE_EVAL = 'live_eval', 'Live eval'
    LIVE_SESSION_COMPARE = 'live_session_compare', 'Live session compare'


class ExperimentRunStatus(models.TextChoices):
    READY = 'READY', 'Ready'
    RUNNING = 'RUNNING', 'Running'
    SUCCESS = 'SUCCESS', 'Success'
    PARTIAL = 'PARTIAL', 'Partial'
    FAILED = 'FAILED', 'Failed'


class ExperimentCandidateType(models.TextChoices):
    THRESHOLD_CHALLENGER = 'threshold_challenger', 'Threshold challenger'
    CALIBRATION_VARIANT = 'calibration_variant', 'Calibration variant'
    RISK_GATE_VARIANT = 'risk_gate_variant', 'Risk gate variant'
    SIZING_VARIANT = 'sizing_variant', 'Sizing variant'
    SHORTLIST_VARIANT = 'shortlist_variant', 'Shortlist variant'
    OPPORTUNITY_VARIANT = 'opportunity_variant', 'Opportunity variant'
    LEARNING_WEIGHT_VARIANT = 'learning_weight_variant', 'Learning weight variant'


class ExperimentCandidateReadinessStatus(models.TextChoices):
    READY = 'READY', 'Ready'
    NEEDS_MORE_DATA = 'NEEDS_MORE_DATA', 'Needs more data'
    BLOCKED = 'BLOCKED', 'Blocked'
    DEFERRED = 'DEFERRED', 'Deferred'


class ChampionChallengerComparisonStatus(models.TextChoices):
    IMPROVED = 'IMPROVED', 'Improved'
    DEGRADED = 'DEGRADED', 'Degraded'
    MIXED = 'MIXED', 'Mixed'
    INCONCLUSIVE = 'INCONCLUSIVE', 'Inconclusive'
    NEEDS_MORE_DATA = 'NEEDS_MORE_DATA', 'Needs more data'


class ExperimentPromotionRecommendationType(models.TextChoices):
    PROMOTE_TO_MANUAL_REVIEW = 'PROMOTE_TO_MANUAL_REVIEW', 'Promote to manual review'
    KEEP_BASELINE = 'KEEP_BASELINE', 'Keep baseline'
    REQUIRE_MORE_DATA = 'REQUIRE_MORE_DATA', 'Require more data'
    REJECT_CHALLENGER = 'REJECT_CHALLENGER', 'Reject challenger'
    BUNDLE_WITH_OTHER_CHANGES = 'BUNDLE_WITH_OTHER_CHANGES', 'Bundle with other changes'
    REORDER_EXPERIMENT_PRIORITY = 'REORDER_EXPERIMENT_PRIORITY', 'Reorder experiment priority'


class StrategyProfile(TimeStampedModel):
    name = models.CharField(max_length=96)
    slug = models.SlugField(max_length=128, unique=True)
    description = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    profile_type = models.CharField(max_length=24, choices=StrategyProfileType.choices, default=StrategyProfileType.BALANCED)
    market_scope = models.CharField(max_length=16, choices=StrategyMarketScope.choices, default=StrategyMarketScope.MIXED)
    config = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['name', 'id']
        indexes = [
            models.Index(fields=['is_active', 'profile_type']),
            models.Index(fields=['market_scope', 'is_active']),
        ]


class ExperimentRun(TimeStampedModel):
    strategy_profile = models.ForeignKey(StrategyProfile, on_delete=models.CASCADE, related_name='experiment_runs')
    run_type = models.CharField(max_length=24, choices=ExperimentRunType.choices)

    related_replay_run = models.ForeignKey(ReplayRun, null=True, blank=True, on_delete=models.SET_NULL, related_name='experiment_runs')
    related_evaluation_run = models.ForeignKey(EvaluationRun, null=True, blank=True, on_delete=models.SET_NULL, related_name='experiment_runs')
    related_continuous_session = models.ForeignKey(
        ContinuousDemoSession,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='experiment_runs',
    )

    status = models.CharField(max_length=16, choices=ExperimentRunStatus.choices, default=ExperimentRunStatus.READY)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    summary = models.CharField(max_length=255, blank=True)
    details = models.JSONField(default=dict, blank=True)
    normalized_metrics = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['run_type', 'status']),
            models.Index(fields=['strategy_profile', '-created_at']),
        ]


class TuningExperimentRun(TimeStampedModel):
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    linked_tuning_review_run = models.ForeignKey(
        'tuning_board.TuningReviewRun',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='tuning_experiment_runs',
    )
    candidate_count = models.PositiveIntegerField(default=0)
    comparison_count = models.PositiveIntegerField(default=0)
    improved_count = models.PositiveIntegerField(default=0)
    degraded_count = models.PositiveIntegerField(default=0)
    require_more_data_count = models.PositiveIntegerField(default=0)
    recommendation_summary = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']


class ExperimentCandidate(TimeStampedModel):
    run = models.ForeignKey(TuningExperimentRun, on_delete=models.CASCADE, related_name='candidates')
    linked_tuning_proposal = models.ForeignKey(
        'tuning_board.TuningProposal',
        on_delete=models.CASCADE,
        related_name='experiment_candidates',
    )
    linked_tuning_bundle = models.ForeignKey(
        'tuning_board.TuningProposalBundle',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='experiment_candidates',
    )
    candidate_type = models.CharField(max_length=40, choices=ExperimentCandidateType.choices)
    baseline_reference = models.CharField(max_length=120, default='champion_baseline')
    challenger_label = models.CharField(max_length=120)
    experiment_scope = models.CharField(max_length=24, choices=(('global', 'Global'), ('provider', 'Provider'), ('category', 'Category'), ('horizon_band', 'Horizon band'), ('model_mode', 'Model mode')))
    readiness_status = models.CharField(max_length=24, choices=ExperimentCandidateReadinessStatus.choices, default=ExperimentCandidateReadinessStatus.NEEDS_MORE_DATA)
    rationale = models.CharField(max_length=255)
    blockers = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['readiness_status', '-created_at']),
            models.Index(fields=['candidate_type', '-created_at']),
        ]


class TuningChampionChallengerComparison(TimeStampedModel):
    run = models.ForeignKey(TuningExperimentRun, on_delete=models.CASCADE, related_name='comparisons')
    linked_candidate = models.ForeignKey(ExperimentCandidate, on_delete=models.CASCADE, related_name='comparisons')
    baseline_label = models.CharField(max_length=120)
    challenger_label = models.CharField(max_length=120)
    comparison_status = models.CharField(max_length=24, choices=ChampionChallengerComparisonStatus.choices)
    compared_metrics = models.JSONField(default=dict, blank=True)
    sample_count = models.PositiveIntegerField(default=0)
    confidence_score = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['comparison_status', '-created_at']),
        ]


class ExperimentPromotionRecommendation(TimeStampedModel):
    run = models.ForeignKey(TuningExperimentRun, on_delete=models.CASCADE, related_name='promotion_recommendations')
    target_candidate = models.ForeignKey(
        ExperimentCandidate,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='promotion_recommendations',
    )
    target_comparison = models.ForeignKey(
        TuningChampionChallengerComparison,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='promotion_recommendations',
    )
    recommendation_type = models.CharField(max_length=40, choices=ExperimentPromotionRecommendationType.choices)
    rationale = models.CharField(max_length=255)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    blockers = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['recommendation_type', '-created_at']),
        ]

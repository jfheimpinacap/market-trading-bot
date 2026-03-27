from decimal import Decimal

from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel
from apps.prediction_training.models import PredictionModelArtifact


class ChallengerRecommendationCode(models.TextChoices):
    KEEP_CHAMPION = 'KEEP_CHAMPION', 'Keep champion'
    CHALLENGER_PROMISING = 'CHALLENGER_PROMISING', 'Challenger promising'
    CHALLENGER_UNDERPERFORMS = 'CHALLENGER_UNDERPERFORMS', 'Challenger underperforms'
    REVIEW_MANUALLY = 'REVIEW_MANUALLY', 'Review manually'


class ChampionChallengerRunStatus(models.TextChoices):
    RUNNING = 'RUNNING', 'Running'
    COMPLETED = 'COMPLETED', 'Completed'
    FAILED = 'FAILED', 'Failed'


class StackProfileBinding(TimeStampedModel):
    name = models.CharField(max_length=96)
    is_champion = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    prediction_model_artifact = models.ForeignKey(
        PredictionModelArtifact,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='stack_bindings',
    )
    prediction_profile_slug = models.CharField(max_length=96, blank=True)
    research_profile_slug = models.CharField(max_length=96, blank=True)
    signal_profile_slug = models.CharField(max_length=96, blank=True)
    opportunity_supervisor_profile_slug = models.CharField(max_length=96, blank=True)
    mission_control_profile_slug = models.CharField(max_length=96, blank=True)
    portfolio_governor_profile_slug = models.CharField(max_length=96, blank=True)
    execution_profile = models.CharField(max_length=40, default='balanced_paper')

    runtime_constraints_snapshot = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-is_champion', '-created_at', '-id']


class ChampionChallengerRun(TimeStampedModel):
    champion_binding = models.ForeignKey(StackProfileBinding, on_delete=models.PROTECT, related_name='champion_runs')
    challenger_binding = models.ForeignKey(StackProfileBinding, on_delete=models.PROTECT, related_name='challenger_runs')

    status = models.CharField(max_length=16, choices=ChampionChallengerRunStatus.choices, default=ChampionChallengerRunStatus.RUNNING)
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)

    markets_evaluated = models.PositiveIntegerField(default=0)
    opportunities_compared = models.PositiveIntegerField(default=0)
    proposals_compared = models.PositiveIntegerField(default=0)
    fills_compared = models.PositiveIntegerField(default=0)
    pnl_delta_execution_adjusted = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))

    recommendation_code = models.CharField(
        max_length=32,
        choices=ChallengerRecommendationCode.choices,
        default=ChallengerRecommendationCode.REVIEW_MANUALLY,
    )
    recommendation_reasons = models.JSONField(default=list, blank=True)
    summary = models.CharField(max_length=255, blank=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class ShadowComparisonResult(TimeStampedModel):
    run = models.OneToOneField(ChampionChallengerRun, on_delete=models.CASCADE, related_name='comparison_result')
    champion_metrics = models.JSONField(default=dict, blank=True)
    challenger_metrics = models.JSONField(default=dict, blank=True)
    deltas = models.JSONField(default=dict, blank=True)
    decision_divergence_rate = models.DecimalField(max_digits=7, decimal_places=4, default=0)

    class Meta:
        ordering = ['-created_at', '-id']

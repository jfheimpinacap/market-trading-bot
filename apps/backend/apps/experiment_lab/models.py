from django.db import models

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

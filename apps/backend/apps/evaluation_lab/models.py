from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel
from apps.continuous_demo.models import ContinuousDemoSession
from apps.semi_auto_demo.models import SemiAutoRun


class EvaluationRunStatus(models.TextChoices):
    READY = 'READY', 'Ready'
    IN_PROGRESS = 'IN_PROGRESS', 'In progress'
    FAILED = 'FAILED', 'Failed'


class EvaluationScope(models.TextChoices):
    SESSION = 'session', 'Session'
    RECENT_WINDOW = 'recent_window', 'Recent window'
    CUSTOM = 'custom', 'Custom'


class EvaluationMarketScope(models.TextChoices):
    DEMO_ONLY = 'demo_only', 'Demo only'
    REAL_ONLY = 'real_only', 'Real only'
    MIXED = 'mixed', 'Mixed'


class EvaluationRun(TimeStampedModel):
    related_continuous_session = models.ForeignKey(
        ContinuousDemoSession,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='evaluation_runs',
    )
    related_semi_auto_run = models.ForeignKey(
        SemiAutoRun,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='evaluation_runs',
    )
    evaluation_scope = models.CharField(max_length=24, choices=EvaluationScope.choices, default=EvaluationScope.SESSION)
    market_scope = models.CharField(max_length=16, choices=EvaluationMarketScope.choices, default=EvaluationMarketScope.MIXED)
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=EvaluationRunStatus.choices, default=EvaluationRunStatus.IN_PROGRESS)
    summary = models.CharField(max_length=255, blank=True)
    guidance = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']
        indexes = [
            models.Index(fields=['status', '-started_at']),
            models.Index(fields=['evaluation_scope', 'market_scope']),
        ]


class EvaluationMetricSet(TimeStampedModel):
    run = models.OneToOneField(EvaluationRun, on_delete=models.CASCADE, related_name='metric_set')
    cycles_count = models.PositiveIntegerField(default=0)
    proposals_generated = models.PositiveIntegerField(default=0)
    auto_executed_count = models.PositiveIntegerField(default=0)
    approval_required_count = models.PositiveIntegerField(default=0)
    blocked_count = models.PositiveIntegerField(default=0)
    pending_approvals_count = models.PositiveIntegerField(default=0)
    trades_executed_count = models.PositiveIntegerField(default=0)
    reviews_generated_count = models.PositiveIntegerField(default=0)
    favorable_reviews_count = models.PositiveIntegerField(default=0)
    neutral_reviews_count = models.PositiveIntegerField(default=0)
    unfavorable_reviews_count = models.PositiveIntegerField(default=0)
    approval_rate = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    block_rate = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    auto_execution_rate = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    favorable_review_rate = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    total_realized_pnl = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_unrealized_pnl = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_pnl = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    ending_equity = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    equity_delta = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    safety_events_count = models.PositiveIntegerField(default=0)
    cooldown_count = models.PositiveIntegerField(default=0)
    hard_stop_count = models.PositiveIntegerField(default=0)
    kill_switch_count = models.PositiveIntegerField(default=0)
    error_count = models.PositiveIntegerField(default=0)

    proposal_to_execution_ratio = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    execution_to_review_ratio = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    unfavorable_review_streak = models.PositiveIntegerField(default=0)
    average_pnl_per_trade = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    average_proposal_score = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    average_confidence = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    percent_real_market_trades = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    percent_demo_market_trades = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    percent_auto_approved = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    percent_manual_approved = models.DecimalField(max_digits=7, decimal_places=4, default=0)

    class Meta:
        ordering = ['-run__started_at', '-id']

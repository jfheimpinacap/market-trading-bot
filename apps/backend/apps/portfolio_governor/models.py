from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel


class PortfolioThrottleState(models.TextChoices):
    NORMAL = 'NORMAL', 'Normal'
    CAUTION = 'CAUTION', 'Caution'
    THROTTLED = 'THROTTLED', 'Throttled'
    BLOCK_NEW_ENTRIES = 'BLOCK_NEW_ENTRIES', 'Block new entries'
    FORCE_REDUCE = 'FORCE_REDUCE', 'Force reduce'


class PortfolioExposureSnapshot(TimeStampedModel):
    total_equity = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    available_cash = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_exposure = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    open_positions = models.PositiveIntegerField(default=0)
    unrealized_pnl = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    recent_drawdown_pct = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    cash_reserve_ratio = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    concentration_market_ratio = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    concentration_provider_ratio = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    exposure_by_market = models.JSONField(default=list, blank=True)
    exposure_by_provider = models.JSONField(default=list, blank=True)
    exposure_by_category = models.JSONField(default=list, blank=True)
    created_at_snapshot = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at_snapshot', '-id']


class PortfolioThrottleDecision(TimeStampedModel):
    state = models.CharField(max_length=24, choices=PortfolioThrottleState.choices, default=PortfolioThrottleState.NORMAL)
    rationale = models.TextField(blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    recommended_max_new_positions = models.PositiveIntegerField(default=3)
    recommended_max_size_multiplier = models.DecimalField(max_digits=8, decimal_places=4, default=1)
    regime_signals = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at_decision = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at_decision', '-id']


class PortfolioGovernanceRunStatus(models.TextChoices):
    RUNNING = 'RUNNING', 'Running'
    COMPLETED = 'COMPLETED', 'Completed'
    FAILED = 'FAILED', 'Failed'


class PortfolioGovernanceRun(TimeStampedModel):
    status = models.CharField(max_length=16, choices=PortfolioGovernanceRunStatus.choices, default=PortfolioGovernanceRunStatus.RUNNING)
    profile_slug = models.CharField(max_length=64, blank=True)
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)
    exposure_snapshot = models.ForeignKey(PortfolioExposureSnapshot, null=True, blank=True, on_delete=models.SET_NULL, related_name='governance_runs')
    throttle_decision = models.ForeignKey(PortfolioThrottleDecision, null=True, blank=True, on_delete=models.SET_NULL, related_name='governance_runs')
    summary = models.CharField(max_length=255, blank=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']

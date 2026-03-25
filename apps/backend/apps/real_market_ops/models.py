from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel


class RealMarketRunStatus(models.TextChoices):
    SUCCESS = 'SUCCESS', 'Success'
    PARTIAL = 'PARTIAL', 'Partial'
    FAILED = 'FAILED', 'Failed'
    SKIPPED = 'SKIPPED', 'Skipped'


class RealMarketRunTrigger(models.TextChoices):
    CONTINUOUS_DEMO = 'continuous_demo', 'Continuous demo'
    AUTOMATION = 'automation', 'Automation'
    MANUAL = 'manual', 'Manual'


class ProviderScope(models.TextChoices):
    ALL = 'all', 'All'
    KALSHI = 'kalshi', 'Kalshi'
    POLYMARKET = 'polymarket', 'Polymarket'


class MarketScope(models.TextChoices):
    ACTIVE_ONLY = 'active_only', 'Active only'
    CURATED = 'curated', 'Curated'
    RECENT_ONLY = 'recent_only', 'Recent only'


class RealScopeConfig(TimeStampedModel):
    enabled = models.BooleanField(default=False)
    provider_scope = models.CharField(max_length=24, choices=ProviderScope.choices, default=ProviderScope.ALL)
    market_scope = models.CharField(max_length=24, choices=MarketScope.choices, default=MarketScope.ACTIVE_ONLY)
    max_real_markets_per_cycle = models.PositiveIntegerField(default=8)
    max_real_auto_trades_per_cycle = models.PositiveIntegerField(default=1)
    max_real_exposure_total = models.DecimalField(max_digits=14, decimal_places=2, default=2500)
    max_real_exposure_per_market = models.DecimalField(max_digits=14, decimal_places=2, default=500)
    require_fresh_sync = models.BooleanField(default=True)
    stale_data_blocks_execution = models.BooleanField(default=True)
    degraded_provider_blocks_execution = models.BooleanField(default=True)
    min_liquidity_threshold = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    min_volume_threshold = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    allowed_categories = models.JSONField(default=list, blank=True)
    exclude_categories = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['id']


class RealMarketOperationRun(TimeStampedModel):
    status = models.CharField(max_length=12, choices=RealMarketRunStatus.choices, default=RealMarketRunStatus.SUCCESS)
    triggered_from = models.CharField(max_length=24, choices=RealMarketRunTrigger.choices, default=RealMarketRunTrigger.MANUAL)
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)

    providers_considered = models.PositiveIntegerField(default=0)
    markets_considered = models.PositiveIntegerField(default=0)
    markets_eligible = models.PositiveIntegerField(default=0)
    proposals_generated = models.PositiveIntegerField(default=0)
    auto_executed_count = models.PositiveIntegerField(default=0)
    approval_required_count = models.PositiveIntegerField(default=0)
    blocked_count = models.PositiveIntegerField(default=0)
    skipped_stale_count = models.PositiveIntegerField(default=0)
    skipped_degraded_provider_count = models.PositiveIntegerField(default=0)
    skipped_no_pricing_count = models.PositiveIntegerField(default=0)

    summary = models.CharField(max_length=255, blank=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']

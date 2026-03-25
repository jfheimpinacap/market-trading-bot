from django.db import models

from apps.common.models import TimeStampedModel
from apps.markets.models import ProviderSlug


class ProviderSyncType(models.TextChoices):
    FULL = 'full', 'Full'
    INCREMENTAL = 'incremental', 'Incremental'
    SINGLE_MARKET = 'single_market', 'Single market'
    ACTIVE_ONLY = 'active_only', 'Active only'


class ProviderSyncStatus(models.TextChoices):
    RUNNING = 'RUNNING', 'Running'
    SUCCESS = 'SUCCESS', 'Success'
    PARTIAL = 'PARTIAL', 'Partial'
    FAILED = 'FAILED', 'Failed'


class ProviderSyncRun(TimeStampedModel):
    provider = models.CharField(max_length=24, choices=ProviderSlug.choices)
    sync_type = models.CharField(max_length=24, choices=ProviderSyncType.choices, default=ProviderSyncType.FULL)
    status = models.CharField(max_length=16, choices=ProviderSyncStatus.choices, default=ProviderSyncStatus.RUNNING)
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)
    triggered_from = models.CharField(max_length=64, blank=True, default='api')

    markets_seen = models.PositiveIntegerField(default=0)
    markets_created = models.PositiveIntegerField(default=0)
    markets_updated = models.PositiveIntegerField(default=0)
    snapshots_created = models.PositiveIntegerField(default=0)
    errors_count = models.PositiveIntegerField(default=0)

    summary = models.TextField(blank=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']
        indexes = [
            models.Index(fields=['provider', '-started_at']),
            models.Index(fields=['status', '-started_at']),
        ]

    def __str__(self) -> str:
        return f'{self.provider}:{self.sync_type}:{self.status}'

from django.db import models
from django.utils.text import slugify

from apps.common.models import TimeStampedModel


class ProviderSlug(models.TextChoices):
    KALSHI = 'kalshi', 'Kalshi'
    POLYMARKET = 'polymarket', 'Polymarket'
    OTHER = 'other', 'Other'


class EventStatus(models.TextChoices):
    DRAFT = 'draft', 'Draft'
    UPCOMING = 'upcoming', 'Upcoming'
    OPEN = 'open', 'Open'
    CLOSED = 'closed', 'Closed'
    RESOLVED = 'resolved', 'Resolved'
    CANCELLED = 'cancelled', 'Cancelled'
    ARCHIVED = 'archived', 'Archived'


class MarketStatus(models.TextChoices):
    DRAFT = 'draft', 'Draft'
    OPEN = 'open', 'Open'
    PAUSED = 'paused', 'Paused'
    CLOSED = 'closed', 'Closed'
    RESOLVED = 'resolved', 'Resolved'
    CANCELLED = 'cancelled', 'Cancelled'
    ARCHIVED = 'archived', 'Archived'


class MarketType(models.TextChoices):
    BINARY = 'binary', 'Binary'
    CATEGORICAL = 'categorical', 'Categorical'
    SCALAR = 'scalar', 'Scalar'
    MULTI_OUTCOME = 'multi_outcome', 'Multi-outcome'
    OTHER = 'other', 'Other'


class OutcomeType(models.TextChoices):
    YES_NO = 'yes_no', 'Yes/No'
    MULTIPLE_CHOICE = 'multiple_choice', 'Multiple choice'
    NUMERIC_RANGE = 'numeric_range', 'Numeric range'
    OTHER = 'other', 'Other'




class MarketSourceType(models.TextChoices):
    DEMO = 'demo', 'Demo/Local'
    REAL_READ_ONLY = 'real_read_only', 'Real Read-only'


class RuleSourceType(models.TextChoices):
    PROVIDER = 'provider', 'Provider'
    INTERNAL = 'internal', 'Internal'
    MANUAL = 'manual', 'Manual'
    IMPORTED = 'imported', 'Imported'


class Provider(TimeStampedModel):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=64, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    base_url = models.URLField(blank=True)
    api_base_url = models.URLField(blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self) -> str:
        return self.name


class Event(TimeStampedModel):
    provider = models.ForeignKey(
        Provider,
        on_delete=models.PROTECT,
        related_name='events',
    )
    provider_event_id = models.CharField(max_length=128, null=True, blank=True)
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, blank=True)
    category = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=EventStatus.choices,
        default=EventStatus.DRAFT,
    )
    open_time = models.DateTimeField(null=True, blank=True)
    close_time = models.DateTimeField(null=True, blank=True)
    resolution_time = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    source_type = models.CharField(
        max_length=24,
        choices=MarketSourceType.choices,
        default=MarketSourceType.DEMO,
    )

    class Meta:
        ordering = ['title']
        constraints = [
            models.UniqueConstraint(
                fields=['provider', 'provider_event_id'],
                condition=models.Q(provider_event_id__isnull=False),
                name='markets_event_provider_provider_event_id_uniq',
            ),
            models.UniqueConstraint(
                fields=['provider', 'slug'],
                name='markets_event_provider_slug_uniq',
            ),
        ]
        indexes = [
            models.Index(fields=['provider', 'status']),
            models.Index(fields=['provider', 'category']),
            models.Index(fields=['open_time']),
            models.Index(fields=['close_time']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug and self.title:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f'{self.provider.slug}: {self.title}'


class Market(TimeStampedModel):
    provider = models.ForeignKey(
        Provider,
        on_delete=models.PROTECT,
        related_name='markets',
    )
    event = models.ForeignKey(
        Event,
        on_delete=models.PROTECT,
        related_name='markets',
        null=True,
        blank=True,
    )
    provider_market_id = models.CharField(max_length=128, null=True, blank=True)
    ticker = models.CharField(max_length=64, blank=True)
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, blank=True)
    category = models.CharField(max_length=100, blank=True)
    market_type = models.CharField(
        max_length=24,
        choices=MarketType.choices,
        default=MarketType.BINARY,
    )
    outcome_type = models.CharField(
        max_length=24,
        choices=OutcomeType.choices,
        default=OutcomeType.YES_NO,
    )
    status = models.CharField(
        max_length=20,
        choices=MarketStatus.choices,
        default=MarketStatus.DRAFT,
    )
    resolution_source = models.CharField(max_length=255, blank=True)
    short_rules = models.TextField(blank=True)
    url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    open_time = models.DateTimeField(null=True, blank=True)
    close_time = models.DateTimeField(null=True, blank=True)
    resolution_time = models.DateTimeField(null=True, blank=True)
    current_market_probability = models.DecimalField(max_digits=7, decimal_places=4, null=True, blank=True)
    current_yes_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    current_no_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    liquidity = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True)
    volume_24h = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True)
    volume_total = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True)
    spread_bps = models.PositiveIntegerField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    source_type = models.CharField(
        max_length=24,
        choices=MarketSourceType.choices,
        default=MarketSourceType.DEMO,
    )

    class Meta:
        ordering = ['title']
        constraints = [
            models.UniqueConstraint(
                fields=['provider', 'provider_market_id'],
                condition=models.Q(provider_market_id__isnull=False),
                name='markets_market_provider_provider_market_id_uniq',
            ),
            models.UniqueConstraint(
                fields=['provider', 'slug'],
                name='markets_market_provider_slug_uniq',
            ),
        ]
        indexes = [
            models.Index(fields=['provider', 'status']),
            models.Index(fields=['event', 'status']),
            models.Index(fields=['provider', 'category']),
            models.Index(fields=['close_time']),
            models.Index(fields=['is_active', 'status']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug and self.title:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f'{self.provider.slug}: {self.title}'


class MarketSnapshot(TimeStampedModel):
    market = models.ForeignKey(
        Market,
        on_delete=models.CASCADE,
        related_name='snapshots',
    )
    captured_at = models.DateTimeField()
    market_probability = models.DecimalField(max_digits=7, decimal_places=4, null=True, blank=True)
    yes_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    no_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    last_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    bid = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    ask = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    spread = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    liquidity = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True)
    volume = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True)
    volume_24h = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True)
    open_interest = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-captured_at', '-id']
        constraints = [
            models.UniqueConstraint(
                fields=['market', 'captured_at'],
                name='markets_snapshot_market_captured_at_uniq',
            ),
        ]
        indexes = [
            models.Index(fields=['market', '-captured_at']),
            models.Index(fields=['captured_at']),
        ]

    def __str__(self) -> str:
        return f'{self.market.title} @ {self.captured_at.isoformat()}'


class MarketRule(TimeStampedModel):
    market = models.ForeignKey(
        Market,
        on_delete=models.CASCADE,
        related_name='rules',
    )
    source_type = models.CharField(
        max_length=20,
        choices=RuleSourceType.choices,
        default=RuleSourceType.PROVIDER,
    )
    rule_text = models.TextField()
    resolution_criteria = models.TextField(blank=True)

    class Meta:
        ordering = ['market__title', 'source_type', '-created_at']
        indexes = [
            models.Index(fields=['market', 'source_type']),
        ]

    def __str__(self) -> str:
        return f'{self.market.title} ({self.source_type})'

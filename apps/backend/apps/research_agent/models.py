from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.common.models import TimeStampedModel


class NarrativeSourceType(models.TextChoices):
    RSS = 'rss', 'RSS'
    NEWS_API = 'news_api', 'News API'
    REDDIT = 'reddit', 'Reddit'
    TWITTER = 'twitter', 'Twitter/X'
    MANUAL = 'manual', 'Manual'


class NarrativeSentiment(models.TextChoices):
    BULLISH = 'bullish', 'Bullish'
    BEARISH = 'bearish', 'Bearish'
    NEUTRAL = 'neutral', 'Neutral'
    MIXED = 'mixed', 'Mixed'
    UNCERTAIN = 'uncertain', 'Uncertain'


class NarrativeAnalysisStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    COMPLETE = 'complete', 'Complete'
    DEGRADED = 'degraded', 'Degraded'
    FAILED = 'failed', 'Failed'


class NarrativeMarketRelation(models.TextChoices):
    ALIGNMENT = 'alignment', 'Alignment'
    DIVERGENCE = 'divergence', 'Divergence'
    UNCERTAINTY = 'uncertainty', 'Uncertainty'


class ResearchScanRunStatus(models.TextChoices):
    SUCCESS = 'success', 'Success'
    PARTIAL = 'partial', 'Partial'
    FAILED = 'failed', 'Failed'


class NarrativeSource(TimeStampedModel):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=120, unique=True)
    source_type = models.CharField(max_length=20, choices=NarrativeSourceType.choices, default=NarrativeSourceType.RSS)
    feed_url = models.URLField(blank=True)
    is_enabled = models.BooleanField(default=True)
    language = models.CharField(max_length=12, blank=True)
    category = models.CharField(max_length=64, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['name']


class NarrativeItem(TimeStampedModel):
    source = models.ForeignKey(NarrativeSource, on_delete=models.CASCADE, related_name='items')
    external_id = models.CharField(max_length=255, null=True, blank=True)
    title = models.CharField(max_length=512)
    url = models.URLField(max_length=1200)
    published_at = models.DateTimeField(null=True, blank=True)
    raw_text = models.TextField()
    snippet = models.TextField(blank=True)
    author = models.CharField(max_length=255, blank=True)
    source_name = models.CharField(max_length=255, blank=True)
    dedupe_hash = models.CharField(max_length=64, unique=True)
    ingested_at = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-published_at', '-ingested_at', '-id']
        indexes = [models.Index(fields=['source', '-ingested_at']), models.Index(fields=['-published_at'])]


class NarrativeAnalysis(TimeStampedModel):
    narrative_item = models.OneToOneField(NarrativeItem, on_delete=models.CASCADE, related_name='analysis')
    summary = models.TextField(blank=True)
    sentiment = models.CharField(max_length=16, choices=NarrativeSentiment.choices, default=NarrativeSentiment.UNCERTAIN)
    confidence = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal('0.0000'))
    entities = models.JSONField(default=list, blank=True)
    topics = models.JSONField(default=list, blank=True)
    market_relevance_score = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal('0.0000'),
        validators=[MinValueValidator(Decimal('0.0000')), MaxValueValidator(Decimal('1.0000'))],
    )
    analysis_status = models.CharField(max_length=16, choices=NarrativeAnalysisStatus.choices, default=NarrativeAnalysisStatus.PENDING)
    model_name = models.CharField(max_length=120, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class MarketNarrativeLink(TimeStampedModel):
    narrative_item = models.ForeignKey(NarrativeItem, on_delete=models.CASCADE, related_name='market_links')
    market = models.ForeignKey('markets.Market', on_delete=models.CASCADE, related_name='narrative_links')
    link_strength = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal('0.0000'),
        validators=[MinValueValidator(Decimal('0.0000')), MaxValueValidator(Decimal('1.0000'))],
    )
    rationale = models.CharField(max_length=255, blank=True)
    linked_at = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-link_strength', '-linked_at', '-id']
        constraints = [models.UniqueConstraint(fields=['narrative_item', 'market'], name='research_unique_item_market_link')]


class ResearchCandidate(TimeStampedModel):
    market = models.ForeignKey('markets.Market', on_delete=models.CASCADE, related_name='research_candidates')
    narrative_items = models.ManyToManyField(NarrativeItem, related_name='research_candidates', blank=True)
    narrative_pressure = models.DecimalField(max_digits=6, decimal_places=4, default=Decimal('0.0000'))
    sentiment_direction = models.CharField(max_length=16, choices=NarrativeSentiment.choices, default=NarrativeSentiment.UNCERTAIN)
    implied_probability_snapshot = models.DecimalField(max_digits=7, decimal_places=4, null=True, blank=True)
    market_implied_direction = models.CharField(max_length=16, choices=NarrativeSentiment.choices, default=NarrativeSentiment.UNCERTAIN)
    relation = models.CharField(max_length=16, choices=NarrativeMarketRelation.choices, default=NarrativeMarketRelation.UNCERTAINTY)
    divergence_score = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal('0.0000'))
    rss_narrative_contribution = models.DecimalField(max_digits=6, decimal_places=4, default=Decimal('0.0000'))
    social_narrative_contribution = models.DecimalField(max_digits=6, decimal_places=4, default=Decimal('0.0000'))
    source_mix = models.CharField(max_length=24, default='news_only')
    short_thesis = models.CharField(max_length=255, blank=True)
    priority = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-priority', '-updated_at', '-id']
        constraints = [models.UniqueConstraint(fields=['market'], name='research_unique_market_candidate')]


class ResearchScanRun(TimeStampedModel):
    status = models.CharField(max_length=12, choices=ResearchScanRunStatus.choices, default=ResearchScanRunStatus.SUCCESS)
    triggered_by = models.CharField(max_length=32, default='manual')
    sources_scanned = models.PositiveIntegerField(default=0)
    items_created = models.PositiveIntegerField(default=0)
    rss_items_created = models.PositiveIntegerField(default=0)
    reddit_items_created = models.PositiveIntegerField(default=0)
    twitter_items_created = models.PositiveIntegerField(default=0)
    social_items_total = models.PositiveIntegerField(default=0)
    items_deduplicated = models.PositiveIntegerField(default=0)
    analyses_generated = models.PositiveIntegerField(default=0)
    analyses_degraded = models.PositiveIntegerField(default=0)
    candidates_generated = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)
    errors = models.JSONField(default=list, blank=True)
    source_errors = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']

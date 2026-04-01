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


class MarketUniverseScanRunStatus(models.TextChoices):
    RUNNING = 'running', 'Running'
    SUCCESS = 'success', 'Success'
    PARTIAL = 'partial', 'Partial'
    FAILED = 'failed', 'Failed'


class TriageStatus(models.TextChoices):
    SHORTLISTED = 'shortlisted', 'Shortlisted'
    WATCH = 'watch', 'Watch'
    FILTERED_OUT = 'filtered_out', 'Filtered out'


class ResearchFilterProfile(models.TextChoices):
    CONSERVATIVE = 'conservative_scan', 'Conservative scan'
    BALANCED = 'balanced_scan', 'Balanced scan'
    BROAD = 'broad_scan', 'Broad scan'


class NarrativeSignalDirection(models.TextChoices):
    BULLISH_YES = 'bullish_yes', 'Bullish/Yes'
    BEARISH_YES = 'bearish_yes', 'Bearish/Yes'
    UNCLEAR = 'unclear', 'Unclear'
    MIXED = 'mixed', 'Mixed'


class NarrativeSignalStatus(models.TextChoices):
    CANDIDATE = 'candidate', 'Candidate'
    SHORTLISTED = 'shortlisted', 'Shortlisted'
    WATCH = 'watch', 'Watch'
    IGNORE = 'ignore', 'Ignore'


class NarrativeClusterStatus(models.TextChoices):
    EMERGING = 'emerging', 'Emerging'
    CONFIRMED_MULTI_SOURCE = 'confirmed_multi_source', 'Confirmed multi-source'
    NOISY = 'noisy', 'Noisy'
    STALE = 'stale', 'Stale'


class ScanRecommendationType(models.TextChoices):
    SEND_TO_RESEARCH_TRIAGE = 'send_to_research_triage', 'Send to research triage'
    SEND_TO_PREDICTION_CONTEXT = 'send_to_prediction_context', 'Send to prediction context'
    KEEP_ON_WATCHLIST = 'keep_on_watchlist', 'Keep on watchlist'
    IGNORE_NOISE = 'ignore_noise', 'Ignore noise'
    REQUIRE_MANUAL_REVIEW = 'require_manual_review', 'Require manual review'
    REORDER_SCAN_PRIORITY = 'reorder_scan_priority', 'Reorder scan priority'


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


class MarketUniverseScanRun(TimeStampedModel):
    status = models.CharField(max_length=12, choices=MarketUniverseScanRunStatus.choices, default=MarketUniverseScanRunStatus.RUNNING)
    triggered_by = models.CharField(max_length=32, default='manual')
    filter_profile = models.CharField(max_length=32, choices=ResearchFilterProfile.choices, default=ResearchFilterProfile.BALANCED)
    provider_scope = models.JSONField(default=list, blank=True)
    source_scope = models.JSONField(default=list, blank=True)
    markets_considered = models.PositiveIntegerField(default=0)
    markets_filtered_out = models.PositiveIntegerField(default=0)
    markets_shortlisted = models.PositiveIntegerField(default=0)
    markets_watchlist = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)
    summary = models.CharField(max_length=255, blank=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']


class MarketTriageDecision(TimeStampedModel):
    run = models.ForeignKey(MarketUniverseScanRun, on_delete=models.CASCADE, related_name='triage_decisions')
    market = models.ForeignKey('markets.Market', on_delete=models.CASCADE, related_name='triage_decisions')
    triage_status = models.CharField(max_length=16, choices=TriageStatus.choices)
    triage_score = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    exclusion_reasons = models.JSONField(default=list, blank=True)
    flags = models.JSONField(default=list, blank=True)
    narrative_coverage = models.PositiveIntegerField(default=0)
    narrative_relevance = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal('0.0000'))
    narrative_confidence = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal('0.0000'))
    source_mix = models.CharField(max_length=24, default='none')
    rationale = models.CharField(max_length=255, blank=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-triage_score', '-created_at', '-id']
        constraints = [models.UniqueConstraint(fields=['run', 'market'], name='research_unique_run_market_triage_decision')]


class PursuitCandidate(TimeStampedModel):
    run = models.ForeignKey(MarketUniverseScanRun, on_delete=models.CASCADE, related_name='pursuit_candidates')
    triage_decision = models.OneToOneField(MarketTriageDecision, on_delete=models.CASCADE, related_name='pursuit_candidate')
    market = models.ForeignKey('markets.Market', on_delete=models.CASCADE, related_name='pursuit_candidates')
    provider_slug = models.CharField(max_length=64)
    liquidity = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True)
    volume_24h = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True)
    time_to_resolution_hours = models.IntegerField(null=True, blank=True)
    market_probability = models.DecimalField(max_digits=7, decimal_places=4, null=True, blank=True)
    narrative_coverage = models.PositiveIntegerField(default=0)
    narrative_direction = models.CharField(max_length=16, choices=NarrativeSentiment.choices, default=NarrativeSentiment.UNCERTAIN)
    source_mix = models.CharField(max_length=24, default='none')
    triage_score = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    triage_status = models.CharField(max_length=16, choices=TriageStatus.choices)
    rationale = models.CharField(max_length=255, blank=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-triage_score', '-created_at', '-id']
        constraints = [models.UniqueConstraint(fields=['run', 'market'], name='research_unique_run_market_pursuit_candidate')]




class MarketResearchCandidateStatus(models.TextChoices):
    SHORTLIST = 'shortlist', 'Shortlist'
    WATCHLIST = 'watchlist', 'Watchlist'
    IGNORE = 'ignore', 'Ignore'
    NEEDS_REVIEW = 'needs_review', 'Needs review'


class MarketTriageDecisionType(models.TextChoices):
    SEND_TO_PREDICTION = 'send_to_prediction', 'Send to prediction'
    KEEP_ON_WATCHLIST = 'keep_on_watchlist', 'Keep on watchlist'
    IGNORE_MARKET = 'ignore_market', 'Ignore market'
    REQUIRE_MANUAL_REVIEW = 'require_manual_review', 'Require manual review'
    RESEARCH_FOLLOWUP = 'research_followup', 'Research follow-up'


class MarketTriageDecisionStatus(models.TextChoices):
    PROPOSED = 'proposed', 'Proposed'
    REVIEWED = 'reviewed', 'Reviewed'
    CONFIRMED = 'confirmed', 'Confirmed'
    SKIPPED = 'skipped', 'Skipped'


class MarketResearchRecommendationType(models.TextChoices):
    SEND_TO_PREDICTION = 'send_to_prediction', 'Send to prediction'
    RESEARCH_FOLLOWUP = 'research_followup', 'Research follow-up'
    KEEP_ON_WATCHLIST = 'keep_on_watchlist', 'Keep on watchlist'
    IGNORE_LOW_QUALITY = 'ignore_low_quality', 'Ignore low quality'
    IGNORE_LOW_LIQUIDITY = 'ignore_low_liquidity', 'Ignore low liquidity'
    IGNORE_BAD_TIME_HORIZON = 'ignore_bad_time_horizon', 'Ignore bad time horizon'
    REQUIRE_MANUAL_REVIEW = 'require_manual_review', 'Require manual review'
    REORDER_RESEARCH_PRIORITY = 'reorder_research_priority', 'Reorder research priority'


class NarrativeConsensusState(models.TextChoices):
    STRONG_CONSENSUS = 'strong_consensus', 'Strong consensus'
    WEAK_CONSENSUS = 'weak_consensus', 'Weak consensus'
    MIXED = 'mixed', 'Mixed'
    CONFLICTED = 'conflicted', 'Conflicted'
    INSUFFICIENT_SIGNAL = 'insufficient_signal', 'Insufficient signal'


class NarrativeBias(models.TextChoices):
    BULLISH = 'bullish', 'Bullish'
    BEARISH = 'bearish', 'Bearish'
    MIXED = 'mixed', 'Mixed'
    UNCLEAR = 'unclear', 'Unclear'


class NarrativeDivergenceState(models.TextChoices):
    ALIGNED = 'aligned', 'Aligned'
    MODEST_DIVERGENCE = 'modest_divergence', 'Modest divergence'
    HIGH_DIVERGENCE = 'high_divergence', 'High divergence'
    UNCERTAIN = 'uncertain', 'Uncertain'


class ResearchPriorityBucket(models.TextChoices):
    CRITICAL = 'critical', 'Critical'
    HIGH = 'high', 'High'
    MEDIUM = 'medium', 'Medium'
    LOW = 'low', 'Low'
    IGNORE = 'ignore', 'Ignore'


class ResearchHandoffStatus(models.TextChoices):
    READY_FOR_RESEARCH = 'ready_for_research', 'Ready for research'
    WATCHLIST = 'watchlist', 'Watchlist'
    BLOCKED = 'blocked', 'Blocked'
    DEFERRED = 'deferred', 'Deferred'


class NarrativeConsensusRecommendationType(models.TextChoices):
    SEND_TO_RESEARCH_IMMEDIATELY = 'send_to_research_immediately', 'Send to research immediately'
    KEEP_ON_NARRATIVE_WATCHLIST = 'keep_on_narrative_watchlist', 'Keep on narrative watchlist'
    PRIORITIZE_FOR_MARKET_DIVERGENCE_REVIEW = 'prioritize_for_market_divergence_review', 'Prioritize for market divergence review'
    DEFER_FOR_WEAKER_SIGNAL = 'defer_for_weaker_signal', 'Defer for weaker signal'
    BLOCK_FOR_CONFLICTED_NARRATIVE = 'block_for_conflicted_narrative', 'Block for conflicted narrative'
    REQUIRE_MANUAL_REVIEW_FOR_SOURCE_CONFLICT = 'require_manual_review_for_source_conflict', 'Require manual review for source conflict'


class ResearchLiquidityState(models.TextChoices):
    STRONG = 'strong', 'Strong'
    ADEQUATE = 'adequate', 'Adequate'
    WEAK = 'weak', 'Weak'
    INSUFFICIENT = 'insufficient', 'Insufficient'


class ResearchVolumeState(models.TextChoices):
    STRONG = 'strong', 'Strong'
    ADEQUATE = 'adequate', 'Adequate'
    WEAK = 'weak', 'Weak'
    INSUFFICIENT = 'insufficient', 'Insufficient'


class ResearchTimeWindowState(models.TextChoices):
    GOOD_WINDOW = 'good_window', 'Good window'
    SHORT_WINDOW = 'short_window', 'Short window'
    TOO_CLOSE = 'too_close', 'Too close'
    TOO_FAR = 'too_far', 'Too far'


class ResearchMarketActivityState(models.TextChoices):
    ACTIVE = 'active', 'Active'
    MODERATE = 'moderate', 'Moderate'
    STALE = 'stale', 'Stale'
    CLOSED_OR_BLOCKED = 'closed_or_blocked', 'Closed or blocked'


class ResearchStructuralStatus(models.TextChoices):
    PREDICTION_READY = 'prediction_ready', 'Prediction ready'
    WATCHLIST_ONLY = 'watchlist_only', 'Watchlist only'
    DEFERRED = 'deferred', 'Deferred'
    BLOCKED = 'blocked', 'Blocked'


class ResearchPursuitPriorityBucket(models.TextChoices):
    CRITICAL = 'critical', 'Critical'
    HIGH = 'high', 'High'
    MEDIUM = 'medium', 'Medium'
    LOW = 'low', 'Low'
    IGNORE = 'ignore', 'Ignore'


class ResearchPursuitScoreStatus(models.TextChoices):
    READY_FOR_PREDICTION = 'ready_for_prediction', 'Ready for prediction'
    KEEP_ON_RESEARCH_WATCHLIST = 'keep_on_research_watchlist', 'Keep on research watchlist'
    DEFER = 'defer', 'Defer'
    BLOCK = 'block', 'Block'


class PredictionHandoffStatus(models.TextChoices):
    READY = 'ready', 'Ready'
    WATCH = 'watch', 'Watch'
    BLOCKED = 'blocked', 'Blocked'
    DEFERRED = 'deferred', 'Deferred'


class ResearchPursuitRecommendationType(models.TextChoices):
    SEND_TO_PREDICTION_IMMEDIATELY = 'send_to_prediction_immediately', 'Send to prediction immediately'
    KEEP_ON_RESEARCH_WATCHLIST = 'keep_on_research_watchlist', 'Keep on research watchlist'
    DEFER_FOR_LOW_LIQUIDITY = 'defer_for_low_liquidity', 'Defer for low liquidity'
    DEFER_FOR_POOR_TIME_WINDOW = 'defer_for_poor_time_window', 'Defer for poor time window'
    BLOCK_FOR_STALE_MARKET = 'block_for_stale_market', 'Block for stale market'
    PRIORITIZE_FOR_NARRATIVE_DIVERGENCE = 'prioritize_for_narrative_divergence', 'Prioritize for narrative divergence'
    REQUIRE_MANUAL_REVIEW_FOR_STRUCTURAL_CONFLICT = (
        'require_manual_review_for_structural_conflict',
        'Require manual review for structural conflict',
    )


class SourceScanRun(TimeStampedModel):
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    source_counts = models.JSONField(default=dict, blank=True)
    raw_item_count = models.PositiveIntegerField(default=0)
    deduped_item_count = models.PositiveIntegerField(default=0)
    clustered_count = models.PositiveIntegerField(default=0)
    signal_count = models.PositiveIntegerField(default=0)
    ignored_count = models.PositiveIntegerField(default=0)
    recommendation_summary = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']


class NarrativeCluster(TimeStampedModel):
    scan_run = models.ForeignKey(SourceScanRun, on_delete=models.CASCADE, related_name='clusters')
    canonical_topic = models.CharField(max_length=255)
    representative_headline = models.CharField(max_length=512)
    source_types = models.JSONField(default=list, blank=True)
    item_count = models.PositiveIntegerField(default=0)
    first_seen_at = models.DateTimeField(null=True, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    combined_direction = models.CharField(max_length=24, choices=NarrativeSignalDirection.choices, default=NarrativeSignalDirection.UNCLEAR)
    combined_sentiment = models.CharField(max_length=16, choices=NarrativeSentiment.choices, default=NarrativeSentiment.UNCERTAIN)
    cluster_status = models.CharField(max_length=32, choices=NarrativeClusterStatus.choices, default=NarrativeClusterStatus.EMERGING)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-item_count', '-last_seen_at', '-id']


class NarrativeSignal(TimeStampedModel):
    scan_run = models.ForeignKey(SourceScanRun, on_delete=models.CASCADE, related_name='signals')
    canonical_label = models.CharField(max_length=255)
    topic = models.CharField(max_length=255)
    target_market = models.ForeignKey('markets.Market', null=True, blank=True, on_delete=models.SET_NULL, related_name='narrative_signals')
    source_mix = models.JSONField(default=dict, blank=True)
    direction = models.CharField(max_length=24, choices=NarrativeSignalDirection.choices, default=NarrativeSignalDirection.UNCLEAR)
    sentiment_score = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal('0.0000'))
    novelty_score = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal('0.0000'))
    intensity_score = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal('0.0000'))
    source_confidence_score = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal('0.0000'))
    market_divergence_score = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal('0.0000'))
    total_signal_score = models.DecimalField(max_digits=6, decimal_places=4, default=Decimal('0.0000'))
    status = models.CharField(max_length=16, choices=NarrativeSignalStatus.choices, default=NarrativeSignalStatus.CANDIDATE)
    rationale = models.TextField(blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    raw_source_refs = models.JSONField(default=list, blank=True)
    linked_cluster = models.ForeignKey(NarrativeCluster, null=True, blank=True, on_delete=models.SET_NULL, related_name='signals')
    linked_market = models.ForeignKey('markets.Market', null=True, blank=True, on_delete=models.SET_NULL, related_name='linked_narrative_signals')
    created_at_scan = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-total_signal_score', '-created_at_scan', '-id']


class ScanRecommendation(TimeStampedModel):
    scan_run = models.ForeignKey(SourceScanRun, on_delete=models.CASCADE, related_name='recommendations')
    recommendation_type = models.CharField(max_length=48, choices=ScanRecommendationType.choices)
    target_signal = models.ForeignKey(NarrativeSignal, null=True, blank=True, on_delete=models.SET_NULL, related_name='recommendations')
    rationale = models.TextField()
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal('0.0000'))
    blockers = models.JSONField(default=list, blank=True)
    created_at_scan = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at_scan', '-id']


class MarketUniverseRun(TimeStampedModel):
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    total_markets_seen = models.PositiveIntegerField(default=0)
    open_markets_seen = models.PositiveIntegerField(default=0)
    filtered_out_count = models.PositiveIntegerField(default=0)
    shortlisted_count = models.PositiveIntegerField(default=0)
    watchlist_count = models.PositiveIntegerField(default=0)
    ignored_count = models.PositiveIntegerField(default=0)
    source_provider_counts = models.JSONField(default=dict, blank=True)
    recommendation_summary = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']


class MarketResearchCandidate(TimeStampedModel):
    universe_run = models.ForeignKey(MarketUniverseRun, on_delete=models.CASCADE, related_name='candidates')
    linked_market = models.ForeignKey('markets.Market', on_delete=models.CASCADE, related_name='market_research_candidates')
    market_title = models.CharField(max_length=255)
    market_provider = models.CharField(max_length=64)
    category = models.CharField(max_length=100, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    time_to_resolution_hours = models.IntegerField(null=True, blank=True)
    liquidity_score = models.DecimalField(max_digits=6, decimal_places=4, default=Decimal('0.0000'))
    volume_score = models.DecimalField(max_digits=6, decimal_places=4, default=Decimal('0.0000'))
    freshness_score = models.DecimalField(max_digits=6, decimal_places=4, default=Decimal('0.0000'))
    market_quality_score = models.DecimalField(max_digits=6, decimal_places=4, default=Decimal('0.0000'))
    narrative_support_score = models.DecimalField(max_digits=6, decimal_places=4, default=Decimal('0.0000'))
    divergence_score = models.DecimalField(max_digits=6, decimal_places=4, default=Decimal('0.0000'))
    pursue_worthiness_score = models.DecimalField(max_digits=7, decimal_places=4, default=Decimal('0.0000'))
    status = models.CharField(max_length=24, choices=MarketResearchCandidateStatus.choices, default=MarketResearchCandidateStatus.NEEDS_REVIEW)
    rationale = models.TextField(blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    linked_narrative_signals = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-pursue_worthiness_score', '-created_at', '-id']


class MarketTriageDecisionV2(TimeStampedModel):
    linked_candidate = models.ForeignKey(MarketResearchCandidate, on_delete=models.CASCADE, related_name='triage_decisions')
    decision_type = models.CharField(max_length=32, choices=MarketTriageDecisionType.choices)
    decision_status = models.CharField(max_length=24, choices=MarketTriageDecisionStatus.choices, default=MarketTriageDecisionStatus.PROPOSED)
    rationale = models.TextField(blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    blockers = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class MarketResearchRecommendation(TimeStampedModel):
    universe_run = models.ForeignKey(MarketUniverseRun, on_delete=models.CASCADE, related_name='recommendations')
    recommendation_type = models.CharField(max_length=48, choices=MarketResearchRecommendationType.choices)
    target_market = models.ForeignKey('markets.Market', null=True, blank=True, on_delete=models.SET_NULL, related_name='research_recommendations')
    target_candidate = models.ForeignKey(MarketResearchCandidate, null=True, blank=True, on_delete=models.SET_NULL, related_name='recommendations')
    rationale = models.TextField(blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.DecimalField(max_digits=6, decimal_places=4, default=Decimal('0.0000'))
    blockers = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class NarrativeConsensusRun(TimeStampedModel):
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    considered_signal_count = models.PositiveIntegerField(default=0)
    considered_cluster_count = models.PositiveIntegerField(default=0)
    consensus_detected_count = models.PositiveIntegerField(default=0)
    conflict_detected_count = models.PositiveIntegerField(default=0)
    divergence_detected_count = models.PositiveIntegerField(default=0)
    priority_handoff_count = models.PositiveIntegerField(default=0)
    recommendation_summary = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']


class NarrativeConsensusRecord(TimeStampedModel):
    consensus_run = models.ForeignKey(NarrativeConsensusRun, on_delete=models.CASCADE, related_name='records')
    linked_cluster = models.ForeignKey(NarrativeCluster, null=True, blank=True, on_delete=models.SET_NULL, related_name='consensus_records')
    topic_label = models.CharField(max_length=255)
    source_mix = models.JSONField(default=dict, blank=True)
    source_count = models.PositiveIntegerField(default=0)
    consensus_state = models.CharField(max_length=32, choices=NarrativeConsensusState.choices, default=NarrativeConsensusState.INSUFFICIENT_SIGNAL)
    sentiment_direction = models.CharField(max_length=16, choices=NarrativeBias.choices, default=NarrativeBias.UNCLEAR)
    intensity_score = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal('0.0000'))
    novelty_score = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal('0.0000'))
    persistence_score = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal('0.0000'))
    confidence_score = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal('0.0000'))
    summary = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-confidence_score', '-created_at', '-id']


class NarrativeMarketDivergenceRecord(TimeStampedModel):
    consensus_run = models.ForeignKey(NarrativeConsensusRun, on_delete=models.CASCADE, related_name='divergence_records')
    linked_consensus_record = models.ForeignKey(NarrativeConsensusRecord, on_delete=models.CASCADE, related_name='divergence_records')
    linked_market = models.ForeignKey('markets.Market', null=True, blank=True, on_delete=models.SET_NULL, related_name='narrative_divergence_records')
    market_probability = models.DecimalField(max_digits=7, decimal_places=4, null=True, blank=True)
    narrative_bias = models.CharField(max_length=16, choices=NarrativeBias.choices, default=NarrativeBias.UNCLEAR)
    divergence_state = models.CharField(max_length=32, choices=NarrativeDivergenceState.choices, default=NarrativeDivergenceState.UNCERTAIN)
    divergence_score = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal('0.0000'))
    market_context_summary = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-divergence_score', '-created_at', '-id']


class ResearchHandoffPriority(TimeStampedModel):
    consensus_run = models.ForeignKey(NarrativeConsensusRun, on_delete=models.CASCADE, related_name='handoff_priorities')
    linked_consensus_record = models.ForeignKey(NarrativeConsensusRecord, on_delete=models.CASCADE, related_name='handoff_priorities')
    linked_divergence_record = models.ForeignKey(
        NarrativeMarketDivergenceRecord, null=True, blank=True, on_delete=models.SET_NULL, related_name='handoff_priorities'
    )
    linked_market = models.ForeignKey('markets.Market', null=True, blank=True, on_delete=models.SET_NULL, related_name='research_handoff_priorities')
    priority_bucket = models.CharField(max_length=16, choices=ResearchPriorityBucket.choices, default=ResearchPriorityBucket.LOW)
    handoff_status = models.CharField(max_length=24, choices=ResearchHandoffStatus.choices, default=ResearchHandoffStatus.WATCHLIST)
    priority_reason_codes = models.JSONField(default=list, blank=True)
    priority_score = models.DecimalField(max_digits=6, decimal_places=4, default=Decimal('0.0000'))
    handoff_summary = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-priority_score', '-created_at', '-id']


class NarrativeConsensusRecommendation(TimeStampedModel):
    consensus_run = models.ForeignKey(NarrativeConsensusRun, on_delete=models.CASCADE, related_name='recommendations')
    recommendation_type = models.CharField(max_length=64, choices=NarrativeConsensusRecommendationType.choices)
    target_cluster = models.ForeignKey(NarrativeCluster, null=True, blank=True, on_delete=models.SET_NULL, related_name='consensus_recommendations')
    target_market = models.ForeignKey('markets.Market', null=True, blank=True, on_delete=models.SET_NULL, related_name='consensus_recommendations')
    target_handoff = models.ForeignKey(ResearchHandoffPriority, null=True, blank=True, on_delete=models.SET_NULL, related_name='recommendations')
    rationale = models.TextField()
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal('0.0000'))
    blockers = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']


class ResearchPursuitRun(TimeStampedModel):
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    considered_market_count = models.PositiveIntegerField(default=0)
    considered_handoff_count = models.PositiveIntegerField(default=0)
    prediction_ready_count = models.PositiveIntegerField(default=0)
    research_watchlist_count = models.PositiveIntegerField(default=0)
    blocked_count = models.PositiveIntegerField(default=0)
    deferred_count = models.PositiveIntegerField(default=0)
    recommendation_summary = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']


class ResearchStructuralAssessment(TimeStampedModel):
    pursuit_run = models.ForeignKey(ResearchPursuitRun, on_delete=models.CASCADE, related_name='assessments')
    linked_market = models.ForeignKey('markets.Market', on_delete=models.CASCADE, related_name='research_structural_assessments')
    linked_handoff_priority = models.ForeignKey(
        ResearchHandoffPriority, null=True, blank=True, on_delete=models.SET_NULL, related_name='structural_assessments'
    )
    linked_consensus_record = models.ForeignKey(
        NarrativeConsensusRecord, null=True, blank=True, on_delete=models.SET_NULL, related_name='structural_assessments'
    )
    linked_divergence_record = models.ForeignKey(
        NarrativeMarketDivergenceRecord, null=True, blank=True, on_delete=models.SET_NULL, related_name='structural_assessments'
    )
    liquidity_state = models.CharField(max_length=16, choices=ResearchLiquidityState.choices, default=ResearchLiquidityState.INSUFFICIENT)
    volume_state = models.CharField(max_length=16, choices=ResearchVolumeState.choices, default=ResearchVolumeState.INSUFFICIENT)
    time_to_resolution_state = models.CharField(
        max_length=16, choices=ResearchTimeWindowState.choices, default=ResearchTimeWindowState.TOO_CLOSE
    )
    market_activity_state = models.CharField(
        max_length=24, choices=ResearchMarketActivityState.choices, default=ResearchMarketActivityState.CLOSED_OR_BLOCKED
    )
    structural_status = models.CharField(max_length=24, choices=ResearchStructuralStatus.choices, default=ResearchStructuralStatus.DEFERRED)
    assessment_summary = models.TextField(blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']


class ResearchPursuitScore(TimeStampedModel):
    pursuit_run = models.ForeignKey(ResearchPursuitRun, on_delete=models.CASCADE, related_name='scores')
    linked_assessment = models.ForeignKey(ResearchStructuralAssessment, on_delete=models.CASCADE, related_name='scores')
    linked_market = models.ForeignKey('markets.Market', on_delete=models.CASCADE, related_name='research_pursuit_scores')
    pursuit_score = models.DecimalField(max_digits=6, decimal_places=4, default=Decimal('0.0000'))
    priority_bucket = models.CharField(max_length=16, choices=ResearchPursuitPriorityBucket.choices, default=ResearchPursuitPriorityBucket.LOW)
    score_components = models.JSONField(default=dict, blank=True)
    score_status = models.CharField(max_length=32, choices=ResearchPursuitScoreStatus.choices, default=ResearchPursuitScoreStatus.DEFER)
    score_summary = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-pursuit_score', '-created_at', '-id']


class PredictionHandoffCandidate(TimeStampedModel):
    pursuit_run = models.ForeignKey(ResearchPursuitRun, on_delete=models.CASCADE, related_name='prediction_handoffs')
    linked_market = models.ForeignKey('markets.Market', on_delete=models.CASCADE, related_name='prediction_handoff_candidates')
    linked_pursuit_score = models.ForeignKey(ResearchPursuitScore, on_delete=models.CASCADE, related_name='handoff_candidates')
    linked_assessment = models.ForeignKey(ResearchStructuralAssessment, on_delete=models.CASCADE, related_name='handoff_candidates')
    linked_consensus_record = models.ForeignKey(
        NarrativeConsensusRecord, null=True, blank=True, on_delete=models.SET_NULL, related_name='prediction_handoff_candidates'
    )
    linked_divergence_record = models.ForeignKey(
        NarrativeMarketDivergenceRecord, null=True, blank=True, on_delete=models.SET_NULL, related_name='prediction_handoff_candidates'
    )
    handoff_status = models.CharField(max_length=16, choices=PredictionHandoffStatus.choices, default=PredictionHandoffStatus.WATCH)
    handoff_confidence = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal('0.0000'))
    handoff_summary = models.TextField(blank=True)
    handoff_reason_codes = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']


class ResearchPursuitRecommendation(TimeStampedModel):
    pursuit_run = models.ForeignKey(ResearchPursuitRun, on_delete=models.CASCADE, related_name='recommendations')
    recommendation_type = models.CharField(max_length=64, choices=ResearchPursuitRecommendationType.choices)
    target_market = models.ForeignKey('markets.Market', null=True, blank=True, on_delete=models.SET_NULL, related_name='research_pursuit_recommendations')
    target_assessment = models.ForeignKey(
        ResearchStructuralAssessment, null=True, blank=True, on_delete=models.SET_NULL, related_name='recommendations'
    )
    target_handoff = models.ForeignKey(
        PredictionHandoffCandidate, null=True, blank=True, on_delete=models.SET_NULL, related_name='recommendations'
    )
    rationale = models.TextField(blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    confidence = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal('0.0000'))
    blockers = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']

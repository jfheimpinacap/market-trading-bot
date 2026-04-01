from rest_framework import serializers

from apps.research_agent.models import (
    NarrativeConsensusRecommendation,
    NarrativeConsensusRun,
    NarrativeConsensusRecord,
    NarrativeMarketDivergenceRecord,
    ResearchHandoffPriority,
    MarketTriageDecision,
    MarketTriageDecisionV2,
    MarketUniverseRun,
    MarketUniverseScanRun,
    MarketResearchCandidate,
    MarketResearchRecommendation,
    NarrativeCluster,
    NarrativeAnalysis,
    NarrativeItem,
    NarrativeSignal,
    NarrativeSource,
    PursuitCandidate,
    ResearchCandidate,
    ResearchFilterProfile,
    ResearchScanRun,
    ScanRecommendation,
    SourceScanRun,
)


class NarrativeSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NarrativeSource
        fields = (
            'id',
            'name',
            'slug',
            'source_type',
            'feed_url',
            'is_enabled',
            'language',
            'category',
            'metadata',
            'created_at',
            'updated_at',
        )


class NarrativeSourceCreateSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        source_type = attrs.get('source_type')
        feed_url = attrs.get('feed_url', '')
        metadata = attrs.get('metadata') or {}
        if source_type == 'rss' and not feed_url:
            raise serializers.ValidationError({'feed_url': 'RSS source requires feed_url.'})
        if source_type == 'reddit' and not (metadata.get('subreddit') or attrs.get('category')):
            raise serializers.ValidationError({'metadata': 'Reddit source requires metadata.subreddit or category.'})
        if source_type == 'twitter' and not (
            metadata.get('manual_items')
            or metadata.get('endpoint_url')
            or metadata.get('query')
            or metadata.get('account')
            or metadata.get('hashtag')
        ):
            raise serializers.ValidationError(
                {'metadata': 'Twitter source requires metadata.manual_items or metadata.endpoint_url/query/account/hashtag.'}
            )
        return attrs

    class Meta:
        model = NarrativeSource
        fields = ('name', 'slug', 'source_type', 'feed_url', 'is_enabled', 'language', 'category', 'metadata')


class NarrativeAnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = NarrativeAnalysis
        fields = (
            'id',
            'summary',
            'sentiment',
            'confidence',
            'entities',
            'topics',
            'market_relevance_score',
            'analysis_status',
            'model_name',
            'metadata',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class NarrativeItemSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source='source.name', read_only=True)
    source_type = serializers.CharField(source='source.source_type', read_only=True)
    analysis = NarrativeAnalysisSerializer(read_only=True)
    linked_market_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = NarrativeItem
        fields = (
            'id',
            'source',
            'external_id',
            'title',
            'url',
            'published_at',
            'raw_text',
            'snippet',
            'author',
            'source_name',
            'source_type',
            'dedupe_hash',
            'ingested_at',
            'metadata',
            'analysis',
            'linked_market_count',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class ResearchCandidateSerializer(serializers.ModelSerializer):
    market_slug = serializers.CharField(source='market.slug', read_only=True)
    market_title = serializers.CharField(source='market.title', read_only=True)
    linked_item_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = ResearchCandidate
        fields = (
            'id',
            'market',
            'market_slug',
            'market_title',
            'narrative_pressure',
            'sentiment_direction',
            'implied_probability_snapshot',
            'market_implied_direction',
            'relation',
            'divergence_score',
            'rss_narrative_contribution',
            'social_narrative_contribution',
            'source_mix',
            'short_thesis',
            'priority',
            'metadata',
            'linked_item_count',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class ResearchRunRequestSerializer(serializers.Serializer):
    source_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), required=False, allow_empty=False)
    run_analysis = serializers.BooleanField(required=False, default=True)


class ScanRunRequestSerializer(serializers.Serializer):
    source_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), required=False, allow_empty=False)


class ResearchScanRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResearchScanRun
        fields = (
            'id',
            'status',
            'triggered_by',
            'sources_scanned',
            'items_created',
            'rss_items_created',
            'reddit_items_created',
            'twitter_items_created',
            'social_items_total',
            'items_deduplicated',
            'analyses_generated',
            'analyses_degraded',
            'candidates_generated',
            'started_at',
            'finished_at',
            'errors',
            'source_errors',
            'metadata',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class SourceScanRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = SourceScanRun
        fields = (
            'id',
            'started_at',
            'completed_at',
            'source_counts',
            'raw_item_count',
            'deduped_item_count',
            'clustered_count',
            'signal_count',
            'ignored_count',
            'recommendation_summary',
            'metadata',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class NarrativeClusterSerializer(serializers.ModelSerializer):
    class Meta:
        model = NarrativeCluster
        fields = (
            'id',
            'scan_run',
            'canonical_topic',
            'representative_headline',
            'source_types',
            'item_count',
            'first_seen_at',
            'last_seen_at',
            'combined_direction',
            'combined_sentiment',
            'cluster_status',
            'metadata',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class NarrativeSignalSerializer(serializers.ModelSerializer):
    linked_market_slug = serializers.CharField(source='linked_market.slug', read_only=True)
    linked_market_title = serializers.CharField(source='linked_market.title', read_only=True)

    class Meta:
        model = NarrativeSignal
        fields = (
            'id',
            'scan_run',
            'canonical_label',
            'topic',
            'target_market',
            'source_mix',
            'direction',
            'sentiment_score',
            'novelty_score',
            'intensity_score',
            'source_confidence_score',
            'market_divergence_score',
            'total_signal_score',
            'status',
            'rationale',
            'reason_codes',
            'raw_source_refs',
            'linked_cluster',
            'linked_market',
            'linked_market_slug',
            'linked_market_title',
            'created_at_scan',
            'metadata',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class ScanRecommendationSerializer(serializers.ModelSerializer):
    target_signal_label = serializers.CharField(source='target_signal.canonical_label', read_only=True)

    class Meta:
        model = ScanRecommendation
        fields = (
            'id',
            'scan_run',
            'recommendation_type',
            'target_signal',
            'target_signal_label',
            'rationale',
            'reason_codes',
            'confidence',
            'blockers',
            'created_at_scan',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class NarrativeConsensusRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = NarrativeConsensusRun
        fields = '__all__'


class NarrativeConsensusRecordSerializer(serializers.ModelSerializer):
    linked_cluster_topic = serializers.CharField(source='linked_cluster.canonical_topic', read_only=True)

    class Meta:
        model = NarrativeConsensusRecord
        fields = '__all__'


class NarrativeMarketDivergenceRecordSerializer(serializers.ModelSerializer):
    linked_market_slug = serializers.CharField(source='linked_market.slug', read_only=True)
    linked_market_title = serializers.CharField(source='linked_market.title', read_only=True)

    class Meta:
        model = NarrativeMarketDivergenceRecord
        fields = '__all__'


class ResearchHandoffPrioritySerializer(serializers.ModelSerializer):
    linked_market_slug = serializers.CharField(source='linked_market.slug', read_only=True)
    linked_market_title = serializers.CharField(source='linked_market.title', read_only=True)
    topic_label = serializers.CharField(source='linked_consensus_record.topic_label', read_only=True)

    class Meta:
        model = ResearchHandoffPriority
        fields = '__all__'


class NarrativeConsensusRecommendationSerializer(serializers.ModelSerializer):
    target_market_slug = serializers.CharField(source='target_market.slug', read_only=True)
    target_market_title = serializers.CharField(source='target_market.title', read_only=True)

    class Meta:
        model = NarrativeConsensusRecommendation
        fields = '__all__'


class UniverseScanRunRequestSerializer(serializers.Serializer):
    filter_profile = serializers.ChoiceField(choices=ResearchFilterProfile.choices, required=False)
    provider_scope = serializers.ListField(child=serializers.CharField(max_length=64), required=False)
    source_scope = serializers.ListField(child=serializers.CharField(max_length=24), required=False)


class MarketUniverseScanRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketUniverseScanRun
        fields = (
            'id',
            'status',
            'triggered_by',
            'filter_profile',
            'provider_scope',
            'source_scope',
            'markets_considered',
            'markets_filtered_out',
            'markets_shortlisted',
            'markets_watchlist',
            'started_at',
            'finished_at',
            'summary',
            'details',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class MarketTriageDecisionSerializer(serializers.ModelSerializer):
    market_slug = serializers.CharField(source='market.slug', read_only=True)
    market_title = serializers.CharField(source='market.title', read_only=True)

    class Meta:
        model = MarketTriageDecision
        fields = (
            'id',
            'run',
            'market',
            'market_slug',
            'market_title',
            'triage_status',
            'triage_score',
            'exclusion_reasons',
            'flags',
            'narrative_coverage',
            'narrative_relevance',
            'narrative_confidence',
            'source_mix',
            'rationale',
            'details',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class PursuitCandidateSerializer(serializers.ModelSerializer):
    market_slug = serializers.CharField(source='market.slug', read_only=True)
    market_title = serializers.CharField(source='market.title', read_only=True)

    class Meta:
        model = PursuitCandidate
        fields = (
            'id',
            'run',
            'triage_decision',
            'market',
            'market_slug',
            'market_title',
            'provider_slug',
            'liquidity',
            'volume_24h',
            'time_to_resolution_hours',
            'market_probability',
            'narrative_coverage',
            'narrative_direction',
            'source_mix',
            'triage_score',
            'triage_status',
            'rationale',
            'details',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class TriageToPredictionRequestSerializer(serializers.Serializer):
    run_id = serializers.IntegerField(min_value=1)
    limit = serializers.IntegerField(min_value=1, max_value=50, required=False, default=10)


class ResearchUniverseRunRequestSerializer(serializers.Serializer):
    provider_scope = serializers.ListField(child=serializers.CharField(max_length=64), required=False)
    source_scope = serializers.ListField(child=serializers.CharField(max_length=24), required=False)


class MarketUniverseRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketUniverseRun
        fields = (
            'id',
            'started_at',
            'completed_at',
            'total_markets_seen',
            'open_markets_seen',
            'filtered_out_count',
            'shortlisted_count',
            'watchlist_count',
            'ignored_count',
            'source_provider_counts',
            'recommendation_summary',
            'metadata',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class MarketResearchCandidateSerializer(serializers.ModelSerializer):
    market_slug = serializers.CharField(source='linked_market.slug', read_only=True)

    class Meta:
        model = MarketResearchCandidate
        fields = (
            'id',
            'universe_run',
            'linked_market',
            'market_slug',
            'market_title',
            'market_provider',
            'category',
            'end_time',
            'time_to_resolution_hours',
            'liquidity_score',
            'volume_score',
            'freshness_score',
            'market_quality_score',
            'narrative_support_score',
            'divergence_score',
            'pursue_worthiness_score',
            'status',
            'rationale',
            'reason_codes',
            'linked_narrative_signals',
            'metadata',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class MarketTriageDecisionV2Serializer(serializers.ModelSerializer):
    market_title = serializers.CharField(source='linked_candidate.market_title', read_only=True)

    class Meta:
        model = MarketTriageDecisionV2
        fields = (
            'id',
            'linked_candidate',
            'market_title',
            'decision_type',
            'decision_status',
            'rationale',
            'reason_codes',
            'blockers',
            'metadata',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class MarketResearchRecommendationSerializer(serializers.ModelSerializer):
    market_title = serializers.CharField(source='target_candidate.market_title', read_only=True)

    class Meta:
        model = MarketResearchRecommendation
        fields = (
            'id',
            'universe_run',
            'recommendation_type',
            'target_market',
            'target_candidate',
            'market_title',
            'rationale',
            'reason_codes',
            'confidence',
            'blockers',
            'metadata',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields

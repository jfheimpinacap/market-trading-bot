from rest_framework import serializers

from apps.research_agent.models import (
    MarketTriageDecision,
    MarketUniverseScanRun,
    NarrativeAnalysis,
    NarrativeItem,
    NarrativeSource,
    PursuitCandidate,
    ResearchCandidate,
    ResearchFilterProfile,
    ResearchScanRun,
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

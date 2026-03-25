from rest_framework import serializers

from apps.research_agent.models import (
    NarrativeAnalysis,
    NarrativeItem,
    NarrativeSource,
    ResearchCandidate,
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
            'items_deduplicated',
            'analyses_generated',
            'candidates_generated',
            'started_at',
            'finished_at',
            'errors',
            'metadata',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields

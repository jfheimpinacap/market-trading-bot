from rest_framework import serializers

from apps.paper_trading.services.market_pricing import get_paper_tradability

from .models import Event, Market, MarketRule, MarketSnapshot, Provider


class ProviderSerializer(serializers.ModelSerializer):
    event_count = serializers.IntegerField(read_only=True)
    market_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Provider
        fields = (
            'id',
            'name',
            'slug',
            'description',
            'is_active',
            'base_url',
            'api_base_url',
            'notes',
            'event_count',
            'market_count',
            'created_at',
            'updated_at',
        )


class ProviderSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Provider
        fields = ('id', 'name', 'slug', 'is_active')


class EventListSerializer(serializers.ModelSerializer):
    provider = ProviderSummarySerializer(read_only=True)
    market_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Event
        fields = (
            'id',
            'provider',
            'provider_event_id',
            'title',
            'slug',
            'category',
            'status',
            'open_time',
            'close_time',
            'resolution_time',
            'source_type',
            'market_count',
            'created_at',
            'updated_at',
        )


class EventDetailSerializer(EventListSerializer):
    class Meta(EventListSerializer.Meta):
        fields = EventListSerializer.Meta.fields + ('description', 'metadata')


class MarketRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketRule
        fields = ('id', 'source_type', 'rule_text', 'resolution_criteria', 'created_at', 'updated_at')


class MarketSnapshotSerializer(serializers.ModelSerializer):
    market_id = serializers.IntegerField(source='market.id', read_only=True)

    class Meta:
        model = MarketSnapshot
        fields = (
            'id',
            'market_id',
            'captured_at',
            'market_probability',
            'yes_price',
            'no_price',
            'last_price',
            'bid',
            'ask',
            'spread',
            'liquidity',
            'volume',
            'volume_24h',
            'open_interest',
            'metadata',
            'created_at',
            'updated_at',
        )


class MarketListSerializer(serializers.ModelSerializer):
    is_demo = serializers.SerializerMethodField()
    is_real = serializers.SerializerMethodField()
    is_real_data = serializers.SerializerMethodField()
    paper_tradable = serializers.SerializerMethodField()
    paper_tradable_reason = serializers.SerializerMethodField()
    execution_mode = serializers.SerializerMethodField()
    provider = ProviderSummarySerializer(read_only=True)
    event_id = serializers.IntegerField(source='event.id', read_only=True)
    event_title = serializers.CharField(source='event.title', read_only=True)
    snapshot_count = serializers.IntegerField(read_only=True)
    latest_snapshot_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Market
        fields = (
            'id',
            'provider',
            'event_id',
            'event_title',
            'provider_market_id',
            'ticker',
            'title',
            'slug',
            'category',
            'market_type',
            'outcome_type',
            'status',
            'resolution_source',
            'url',
            'is_active',
            'open_time',
            'close_time',
            'resolution_time',
            'current_market_probability',
            'current_yes_price',
            'current_no_price',
            'liquidity',
            'volume_24h',
            'volume_total',
            'spread_bps',
            'source_type',
            'is_demo',
            'is_real',
            'is_real_data',
            'paper_tradable',
            'paper_tradable_reason',
            'execution_mode',
            'snapshot_count',
            'latest_snapshot_at',
            'created_at',
            'updated_at',
        )

    def _tradability(self, obj):
        return get_paper_tradability(obj)

    def get_is_demo(self, obj):
        return obj.source_type == 'demo'

    def get_is_real(self, obj):
        return obj.source_type == 'real_read_only'

    def get_is_real_data(self, obj):
        return self.get_is_real(obj)

    def get_paper_tradable(self, obj):
        return self._tradability(obj).is_tradable

    def get_paper_tradable_reason(self, obj):
        return self._tradability(obj).message

    def get_execution_mode(self, obj):
        return 'paper_demo_only'


class MarketDetailSerializer(MarketListSerializer):
    event = EventDetailSerializer(read_only=True)
    rules = MarketRuleSerializer(many=True, read_only=True)
    recent_snapshots = serializers.SerializerMethodField()

    class Meta(MarketListSerializer.Meta):
        fields = MarketListSerializer.Meta.fields + (
            'event',
            'short_rules',
            'metadata',
            'rules',
            'recent_snapshots',
        )

    def get_recent_snapshots(self, obj):
        snapshots = getattr(obj, 'recent_snapshots_cache', None)
        if snapshots is None:
            snapshots = obj.snapshots.order_by('-captured_at', '-id')[:5]
        return MarketSnapshotSerializer(snapshots, many=True).data


class MarketSystemSummarySerializer(serializers.Serializer):
    total_providers = serializers.IntegerField()
    total_events = serializers.IntegerField()
    total_markets = serializers.IntegerField()
    active_markets = serializers.IntegerField()
    resolved_markets = serializers.IntegerField()
    total_snapshots = serializers.IntegerField()

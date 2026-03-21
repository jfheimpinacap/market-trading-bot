from rest_framework import serializers

from .models import Event, Market, MarketRule, MarketSnapshot, Provider


class ProviderSerializer(serializers.ModelSerializer):
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
            'created_at',
            'updated_at',
        )


class EventSerializer(serializers.ModelSerializer):
    provider = ProviderSerializer(read_only=True)

    class Meta:
        model = Event
        fields = (
            'id',
            'provider',
            'provider_event_id',
            'title',
            'slug',
            'category',
            'description',
            'status',
            'open_time',
            'close_time',
            'resolution_time',
            'metadata',
            'created_at',
            'updated_at',
        )


class MarketRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketRule
        fields = ('id', 'source_type', 'rule_text', 'resolution_criteria', 'created_at', 'updated_at')


class MarketSerializer(serializers.ModelSerializer):
    provider = ProviderSerializer(read_only=True)
    event_id = serializers.IntegerField(source='event.id', read_only=True)
    event_title = serializers.CharField(source='event.title', read_only=True)

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
            'short_rules',
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
            'metadata',
            'created_at',
            'updated_at',
        )


class MarketDetailSerializer(MarketSerializer):
    rules = MarketRuleSerializer(many=True, read_only=True)

    class Meta(MarketSerializer.Meta):
        fields = MarketSerializer.Meta.fields + ('rules',)


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

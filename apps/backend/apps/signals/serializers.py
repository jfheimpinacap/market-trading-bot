from rest_framework import serializers

from apps.signals.models import MarketSignal, MockAgent, SignalRun


class MockAgentSerializer(serializers.ModelSerializer):
    signal_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = MockAgent
        fields = (
            'id',
            'name',
            'slug',
            'description',
            'role_type',
            'is_active',
            'notes',
            'signal_count',
            'created_at',
            'updated_at',
        )


class MarketSignalListSerializer(serializers.ModelSerializer):
    agent = MockAgentSerializer(read_only=True)
    market_title = serializers.CharField(source='market.title', read_only=True)
    market_slug = serializers.CharField(source='market.slug', read_only=True)
    market_status = serializers.CharField(source='market.status', read_only=True)
    market_provider_slug = serializers.CharField(source='market.provider.slug', read_only=True)

    class Meta:
        model = MarketSignal
        fields = (
            'id',
            'market',
            'market_title',
            'market_slug',
            'market_status',
            'market_provider_slug',
            'agent',
            'run',
            'signal_type',
            'status',
            'direction',
            'score',
            'confidence',
            'headline',
            'thesis',
            'signal_probability',
            'market_probability_at_signal',
            'edge_estimate',
            'is_actionable',
            'expires_at',
            'created_at',
            'updated_at',
        )


class MarketSignalDetailSerializer(MarketSignalListSerializer):
    class Meta(MarketSignalListSerializer.Meta):
        fields = MarketSignalListSerializer.Meta.fields + (
            'rationale',
            'metadata',
        )


class SignalRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = SignalRun
        fields = (
            'id',
            'run_type',
            'started_at',
            'finished_at',
            'status',
            'markets_evaluated',
            'signals_created',
            'notes',
            'metadata',
            'created_at',
            'updated_at',
        )


class SignalSummarySerializer(serializers.Serializer):
    total_signals = serializers.IntegerField()
    active_signals = serializers.IntegerField()
    actionable_signals = serializers.IntegerField()
    bullish_signals = serializers.IntegerField()
    bearish_signals = serializers.IntegerField()
    neutral_signals = serializers.IntegerField()
    active_agents = serializers.IntegerField()
    markets_with_signals = serializers.IntegerField()
    latest_signal_at = serializers.DateTimeField(allow_null=True)
    latest_run = SignalRunSerializer(allow_null=True)

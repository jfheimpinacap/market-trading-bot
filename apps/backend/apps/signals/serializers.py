from rest_framework import serializers

from apps.signals.models import MarketSignal, MockAgent, OpportunitySignal, ProposalGateDecision, SignalFusionRun, SignalRun
from apps.signals.services.profiles import SIGNAL_PROFILES


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


class SignalFusionRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = SignalFusionRun
        fields = (
            'id',
            'status',
            'profile_slug',
            'triggered_by',
            'started_at',
            'finished_at',
            'markets_evaluated',
            'signals_created',
            'proposal_ready_count',
            'blocked_count',
            'notes',
            'metadata',
            'created_at',
            'updated_at',
        )


class ProposalGateDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProposalGateDecision
        fields = (
            'should_generate_proposal',
            'proposal_priority',
            'proposal_reason',
            'blocked_reason',
            'metadata',
        )


class OpportunitySignalSerializer(serializers.ModelSerializer):
    market_title = serializers.CharField(source='market.title', read_only=True)
    market_slug = serializers.CharField(source='market.slug', read_only=True)
    market_provider_slug = serializers.CharField(source='market.provider.slug', read_only=True)
    proposal_gate = ProposalGateDecisionSerializer(read_only=True)

    class Meta:
        model = OpportunitySignal
        fields = (
            'id',
            'run',
            'rank',
            'market',
            'market_title',
            'market_slug',
            'market_provider_slug',
            'provider_slug',
            'research_score',
            'triage_score',
            'narrative_direction',
            'narrative_confidence',
            'source_mix',
            'prediction_system_probability',
            'prediction_market_probability',
            'edge',
            'prediction_confidence',
            'risk_level',
            'adjusted_quantity',
            'runtime_constraints',
            'opportunity_score',
            'opportunity_status',
            'rationale',
            'metadata',
            'proposal_gate',
            'created_at',
            'updated_at',
        )


class RunFusionRequestSerializer(serializers.Serializer):
    profile_slug = serializers.ChoiceField(choices=list(SIGNAL_PROFILES.keys()), required=False)
    market_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), required=False)


class RunToProposalRequestSerializer(serializers.Serializer):
    run_id = serializers.IntegerField(min_value=1)
    min_priority = serializers.IntegerField(min_value=0, max_value=100, required=False, default=70)


class SignalBoardSummarySerializer(serializers.Serializer):
    total_opportunities = serializers.IntegerField()
    watch_count = serializers.IntegerField()
    candidate_count = serializers.IntegerField()
    proposal_ready_count = serializers.IntegerField()
    blocked_count = serializers.IntegerField()
    latest_run = SignalFusionRunSerializer(allow_null=True)
    paper_demo_only = serializers.BooleanField()
    real_execution_enabled = serializers.BooleanField()

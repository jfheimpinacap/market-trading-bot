from rest_framework import serializers

from apps.autonomous_trader.models import (
    AutonomousTradeCandidate,
    AutonomousTradeCycleRun,
    AutonomousTradeDecision,
    AutonomousTradeExecution,
    AutonomousTradeOutcome,
    AutonomousTradeWatchRecord,
)


class RunCycleSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, default='operator-ui', allow_blank=True)
    cycle_mode = serializers.CharField(required=False, default='FULL_AUTONOMOUS_PAPER_LOOP')
    limit = serializers.IntegerField(required=False, min_value=1, max_value=100, default=25)


class AutonomousTradeCycleRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomousTradeCycleRun
        fields = '__all__'


class AutonomousTradeCandidateSerializer(serializers.ModelSerializer):
    market_title = serializers.CharField(source='linked_market.title', read_only=True)

    class Meta:
        model = AutonomousTradeCandidate
        fields = '__all__'


class AutonomousTradeDecisionSerializer(serializers.ModelSerializer):
    market_title = serializers.CharField(source='linked_candidate.linked_market.title', read_only=True)

    class Meta:
        model = AutonomousTradeDecision
        fields = '__all__'


class AutonomousTradeExecutionSerializer(serializers.ModelSerializer):
    market_title = serializers.CharField(source='linked_candidate.linked_market.title', read_only=True)

    class Meta:
        model = AutonomousTradeExecution
        fields = '__all__'


class AutonomousTradeWatchRecordSerializer(serializers.ModelSerializer):
    market_title = serializers.CharField(source='linked_execution.linked_candidate.linked_market.title', read_only=True)

    class Meta:
        model = AutonomousTradeWatchRecord
        fields = '__all__'


class AutonomousTradeOutcomeSerializer(serializers.ModelSerializer):
    market_title = serializers.CharField(source='linked_execution.linked_candidate.linked_market.title', read_only=True)

    class Meta:
        model = AutonomousTradeOutcome
        fields = '__all__'

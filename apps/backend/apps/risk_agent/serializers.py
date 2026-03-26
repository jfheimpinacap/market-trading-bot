from decimal import Decimal

from rest_framework import serializers

from apps.markets.models import Market
from apps.prediction_agent.models import PredictionScore
from apps.proposal_engine.models import TradeProposal
from apps.risk_agent.models import PositionWatchEvent, PositionWatchRun, RiskAssessment, RiskSizingDecision
from apps.risk_agent.services import run_position_watch, run_risk_assessment, run_risk_sizing


class RiskAssessmentSerializer(serializers.ModelSerializer):
    market_title = serializers.CharField(source='market.title', read_only=True)

    class Meta:
        model = RiskAssessment
        fields = '__all__'


class RiskSizingDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskSizingDecision
        fields = '__all__'


class PositionWatchEventSerializer(serializers.ModelSerializer):
    market_title = serializers.CharField(source='paper_position.market.title', read_only=True)

    class Meta:
        model = PositionWatchEvent
        fields = '__all__'


class PositionWatchRunSerializer(serializers.ModelSerializer):
    events = PositionWatchEventSerializer(many=True, read_only=True)

    class Meta:
        model = PositionWatchRun
        fields = '__all__'


class RiskAssessRequestSerializer(serializers.Serializer):
    market_id = serializers.PrimaryKeyRelatedField(queryset=Market.objects.all(), source='market', required=False, allow_null=True)
    proposal_id = serializers.PrimaryKeyRelatedField(queryset=TradeProposal.objects.all(), source='proposal', required=False, allow_null=True)
    prediction_score_id = serializers.PrimaryKeyRelatedField(queryset=PredictionScore.objects.all(), source='prediction_score', required=False, allow_null=True)
    metadata = serializers.JSONField(required=False)

    def create(self, validated_data):
        return run_risk_assessment(**validated_data)


class RiskSizeRequestSerializer(serializers.Serializer):
    risk_assessment_id = serializers.PrimaryKeyRelatedField(queryset=RiskAssessment.objects.all(), source='risk_assessment')
    base_quantity = serializers.DecimalField(max_digits=14, decimal_places=4, min_value=Decimal('0.0000'))
    metadata = serializers.JSONField(required=False)

    def create(self, validated_data):
        return run_risk_sizing(**validated_data)


class RiskWatchRequestSerializer(serializers.Serializer):
    metadata = serializers.JSONField(required=False)

    def create(self, validated_data):
        return run_position_watch(metadata=validated_data.get('metadata') or {})

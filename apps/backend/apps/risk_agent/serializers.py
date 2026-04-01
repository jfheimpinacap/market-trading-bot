from decimal import Decimal

from rest_framework import serializers

from apps.markets.models import Market
from apps.prediction_agent.models import PredictionScore
from apps.proposal_engine.models import TradeProposal
from apps.risk_agent.models import (
    AutonomousExecutionReadiness,
    PositionWatchEvent,
    PositionWatchPlan,
    PositionWatchRun,
    RiskIntakeRecommendation,
    RiskApprovalDecision,
    RiskAssessment,
    RiskRuntimeCandidate,
    RiskRuntimeRecommendation,
    RiskRuntimeRun,
    RiskSizingDecision,
    RiskSizingPlan,
)
from apps.risk_agent.services import run_position_watch, run_risk_assessment, run_risk_runtime_review, run_risk_sizing


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


class RiskRuntimeRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskRuntimeRun
        fields = '__all__'


class RiskRuntimeCandidateSerializer(serializers.ModelSerializer):
    market_title = serializers.CharField(source='linked_market.title', read_only=True)

    class Meta:
        model = RiskRuntimeCandidate
        fields = '__all__'


class RiskApprovalDecisionSerializer(serializers.ModelSerializer):
    market_title = serializers.CharField(source='linked_candidate.linked_market.title', read_only=True)
    linked_prediction_assessment = serializers.IntegerField(source='linked_candidate.linked_prediction_assessment_id', read_only=True)

    class Meta:
        model = RiskApprovalDecision
        fields = '__all__'


class RiskSizingPlanSerializer(serializers.ModelSerializer):
    market_title = serializers.CharField(source='linked_candidate.linked_market.title', read_only=True)

    class Meta:
        model = RiskSizingPlan
        fields = '__all__'


class PositionWatchPlanSerializer(serializers.ModelSerializer):
    market_title = serializers.CharField(source='linked_candidate.linked_market.title', read_only=True)

    class Meta:
        model = PositionWatchPlan
        fields = '__all__'


class RiskRuntimeRecommendationSerializer(serializers.ModelSerializer):
    market_title = serializers.CharField(source='target_candidate.linked_market.title', read_only=True)

    class Meta:
        model = RiskRuntimeRecommendation
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


class RiskRuntimeReviewRequestSerializer(serializers.Serializer):
    triggered_by = serializers.CharField(required=False, default='manual')

    def create(self, validated_data):
        return run_risk_runtime_review(triggered_by=validated_data.get('triggered_by', 'manual'))


class AutonomousExecutionReadinessSerializer(serializers.ModelSerializer):
    market_title = serializers.CharField(source='linked_market.title', read_only=True)

    class Meta:
        model = AutonomousExecutionReadiness
        fields = '__all__'


class RiskIntakeRecommendationSerializer(serializers.ModelSerializer):
    market_title = serializers.CharField(source='target_market.title', read_only=True)

    class Meta:
        model = RiskIntakeRecommendation
        fields = '__all__'

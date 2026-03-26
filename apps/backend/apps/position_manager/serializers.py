from rest_framework import serializers

from apps.position_manager.models import PositionExitPlan, PositionLifecycleDecision, PositionLifecycleRun
from apps.position_manager.services import run_position_lifecycle


class PositionExitPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = PositionExitPlan
        fields = '__all__'


class PositionLifecycleDecisionSerializer(serializers.ModelSerializer):
    market_title = serializers.CharField(source='paper_position.market.title', read_only=True)
    market_id = serializers.IntegerField(source='paper_position.market_id', read_only=True)
    position_quantity = serializers.DecimalField(source='paper_position.quantity', max_digits=14, decimal_places=4, read_only=True)
    exit_plan = PositionExitPlanSerializer(read_only=True)

    class Meta:
        model = PositionLifecycleDecision
        fields = '__all__'


class PositionLifecycleRunSerializer(serializers.ModelSerializer):
    decisions = PositionLifecycleDecisionSerializer(many=True, read_only=True)

    class Meta:
        model = PositionLifecycleRun
        fields = '__all__'


class RunLifecycleRequestSerializer(serializers.Serializer):
    metadata = serializers.JSONField(required=False)

    def create(self, validated_data):
        return run_position_lifecycle(metadata=validated_data.get('metadata') or {})

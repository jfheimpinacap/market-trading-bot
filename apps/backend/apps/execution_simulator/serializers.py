from rest_framework import serializers

from apps.execution_simulator.models import PaperExecutionAttempt, PaperFill, PaperOrder, PaperOrderLifecycleRun
from apps.execution_simulator.services.lifecycle import run_execution_lifecycle
from apps.execution_simulator.services.orders import create_order
from apps.markets.models import Market


class PaperExecutionAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaperExecutionAttempt
        fields = '__all__'


class PaperFillSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaperFill
        fields = '__all__'


class PaperOrderSerializer(serializers.ModelSerializer):
    fills = PaperFillSerializer(many=True, read_only=True)
    attempts = PaperExecutionAttemptSerializer(many=True, read_only=True)
    market_title = serializers.CharField(source='market.title', read_only=True)

    class Meta:
        model = PaperOrder
        fields = '__all__'


class PaperOrderLifecycleRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaperOrderLifecycleRun
        fields = '__all__'


class CreateOrderRequestSerializer(serializers.Serializer):
    market_id = serializers.IntegerField()
    side = serializers.CharField()
    requested_quantity = serializers.DecimalField(max_digits=14, decimal_places=4)
    order_type = serializers.CharField(required=False, default='market_like')
    requested_price = serializers.DecimalField(max_digits=12, decimal_places=4, required=False, allow_null=True)
    created_from = serializers.CharField(required=False, default='manual')
    metadata = serializers.JSONField(required=False)
    policy_profile = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def create(self, validated_data):
        market = Market.objects.get(id=validated_data['market_id'])
        return create_order(
            market=market,
            side=validated_data['side'],
            requested_quantity=validated_data['requested_quantity'],
            order_type=validated_data.get('order_type', 'market_like'),
            requested_price=validated_data.get('requested_price'),
            created_from=validated_data.get('created_from', 'manual'),
            metadata=validated_data.get('metadata') or {},
            policy_profile=validated_data.get('policy_profile'),
        )


class RunLifecycleRequestSerializer(serializers.Serializer):
    open_only = serializers.BooleanField(required=False, default=True)
    metadata = serializers.JSONField(required=False)

    def create(self, validated_data):
        return run_execution_lifecycle(
            open_only=validated_data.get('open_only', True),
            metadata=validated_data.get('metadata') or {},
        )

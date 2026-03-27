from rest_framework import serializers

from apps.broker_bridge.models import BrokerBridgeValidation, BrokerDryRun, BrokerOrderIntent


class BrokerBridgeValidationSerializer(serializers.ModelSerializer):
    class Meta:
        model = BrokerBridgeValidation
        fields = '__all__'


class BrokerDryRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = BrokerDryRun
        fields = '__all__'


class BrokerOrderIntentSerializer(serializers.ModelSerializer):
    validations = BrokerBridgeValidationSerializer(many=True, read_only=True)
    dry_runs = BrokerDryRunSerializer(many=True, read_only=True)
    market_title = serializers.CharField(source='market.title', read_only=True)

    class Meta:
        model = BrokerOrderIntent
        fields = '__all__'


class CreateIntentRequestSerializer(serializers.Serializer):
    source_type = serializers.CharField(default='paper_order')
    source_id = serializers.CharField(required=False, allow_blank=True)
    payload = serializers.DictField(required=False)


class ActionMetadataRequestSerializer(serializers.Serializer):
    metadata = serializers.DictField(required=False)

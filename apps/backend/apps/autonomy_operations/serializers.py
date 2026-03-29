from rest_framework import serializers

from apps.autonomy_operations.models import CampaignAttentionSignal, CampaignRuntimeSnapshot, OperationsRecommendation, OperationsRun


class CampaignRuntimeSnapshotSerializer(serializers.ModelSerializer):
    campaign_title = serializers.CharField(source='campaign.title', read_only=True)
    current_step_order = serializers.IntegerField(source='current_step.step_order', read_only=True, allow_null=True)
    current_checkpoint_summary = serializers.CharField(source='current_checkpoint.summary', read_only=True, allow_null=True)

    class Meta:
        model = CampaignRuntimeSnapshot
        fields = '__all__'


class CampaignAttentionSignalSerializer(serializers.ModelSerializer):
    campaign_title = serializers.CharField(source='campaign.title', read_only=True)

    class Meta:
        model = CampaignAttentionSignal
        fields = '__all__'


class OperationsRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = OperationsRun
        fields = '__all__'


class OperationsRecommendationSerializer(serializers.ModelSerializer):
    target_campaign_title = serializers.CharField(source='target_campaign.title', read_only=True)

    class Meta:
        model = OperationsRecommendation
        fields = '__all__'


class RunMonitorSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, allow_blank=True, default='operator-ui')


class SignalActionSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, allow_blank=True, default='operator-ui')

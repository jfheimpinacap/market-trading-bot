from rest_framework import serializers

from apps.autonomy_campaign.models import AutonomyCampaign, AutonomyCampaignCheckpoint, AutonomyCampaignStep


class AutonomyCampaignCheckpointSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomyCampaignCheckpoint
        fields = '__all__'


class AutonomyCampaignStepSerializer(serializers.ModelSerializer):
    domain_slug = serializers.CharField(source='domain.slug', read_only=True)

    class Meta:
        model = AutonomyCampaignStep
        fields = '__all__'


class AutonomyCampaignSerializer(serializers.ModelSerializer):
    steps = AutonomyCampaignStepSerializer(many=True, read_only=True)
    checkpoints = AutonomyCampaignCheckpointSerializer(many=True, read_only=True)

    class Meta:
        model = AutonomyCampaign
        fields = '__all__'


class CreateAutonomyCampaignSerializer(serializers.Serializer):
    source_type = serializers.ChoiceField(choices=['roadmap_plan', 'scenario_run', 'manual_bundle'])
    source_object_id = serializers.CharField()
    title = serializers.CharField(required=False, allow_blank=True)
    summary = serializers.CharField(required=False, allow_blank=True)
    metadata = serializers.JSONField(required=False)


class CampaignActionSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, allow_blank=True)
    reason = serializers.CharField(required=False, allow_blank=True)

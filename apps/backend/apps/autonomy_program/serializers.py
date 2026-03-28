from rest_framework import serializers

from apps.autonomy_program.models import AutonomyProgramState, CampaignConcurrencyRule, CampaignHealthSnapshot, ProgramRecommendation


class AutonomyProgramStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomyProgramState
        fields = '__all__'


class CampaignConcurrencyRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampaignConcurrencyRule
        fields = '__all__'


class CampaignHealthSnapshotSerializer(serializers.ModelSerializer):
    campaign_title = serializers.CharField(source='campaign.title', read_only=True)

    class Meta:
        model = CampaignHealthSnapshot
        fields = '__all__'


class ProgramRecommendationSerializer(serializers.ModelSerializer):
    target_campaign_title = serializers.CharField(source='target_campaign.title', read_only=True)

    class Meta:
        model = ProgramRecommendation
        fields = '__all__'


class RunProgramReviewSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, allow_blank=True)
    apply_pause_gating = serializers.BooleanField(required=False, default=True)

from rest_framework import serializers

from apps.autonomy_advisory.models import AdvisoryArtifact, AdvisoryRecommendation, AdvisoryRun


class AdvisoryArtifactSerializer(serializers.ModelSerializer):
    campaign_title = serializers.CharField(source='campaign.title', read_only=True)

    class Meta:
        model = AdvisoryArtifact
        fields = '__all__'


class AdvisoryRecommendationSerializer(serializers.ModelSerializer):
    campaign_title = serializers.CharField(source='target_campaign.title', read_only=True)

    class Meta:
        model = AdvisoryRecommendation
        fields = '__all__'


class AdvisoryRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdvisoryRun
        fields = '__all__'


class AdvisoryActionSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, allow_blank=True, default='operator-ui')

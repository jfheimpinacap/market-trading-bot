from rest_framework import serializers

from apps.autonomy_advisory_resolution.models import AdvisoryResolution, AdvisoryResolutionRecommendation, AdvisoryResolutionRun


class AdvisoryResolutionSerializer(serializers.ModelSerializer):
    campaign_title = serializers.CharField(source='campaign.title', read_only=True)

    class Meta:
        model = AdvisoryResolution
        fields = '__all__'


class AdvisoryResolutionRecommendationSerializer(serializers.ModelSerializer):
    campaign_title = serializers.CharField(source='advisory_artifact.campaign.title', read_only=True)

    class Meta:
        model = AdvisoryResolutionRecommendation
        fields = '__all__'


class AdvisoryResolutionRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdvisoryResolutionRun
        fields = '__all__'


class AdvisoryResolutionActionSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, allow_blank=True, default='operator-ui', max_length=120)
    rationale = serializers.CharField(required=False, allow_blank=True, max_length=255)
    reason_codes = serializers.ListField(child=serializers.CharField(max_length=64), required=False)

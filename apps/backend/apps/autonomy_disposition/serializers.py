from rest_framework import serializers

from apps.autonomy_disposition.models import CampaignDisposition, DispositionRecommendation, DispositionRun


class CampaignDispositionSerializer(serializers.ModelSerializer):
    campaign_title = serializers.CharField(source='campaign.title', read_only=True)

    class Meta:
        model = CampaignDisposition
        fields = '__all__'


class DispositionRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = DispositionRun
        fields = '__all__'


class DispositionRecommendationSerializer(serializers.ModelSerializer):
    target_campaign_title = serializers.CharField(source='target_campaign.title', read_only=True)

    class Meta:
        model = DispositionRecommendation
        fields = '__all__'


class RunDispositionReviewSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, allow_blank=True, default='operator-ui')


class CampaignDispositionActionSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, allow_blank=True, default='operator-ui')

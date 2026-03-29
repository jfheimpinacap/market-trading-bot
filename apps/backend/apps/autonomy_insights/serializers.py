from rest_framework import serializers

from apps.autonomy_insights.models import CampaignInsight, InsightRecommendation, InsightRun


class CampaignInsightSerializer(serializers.ModelSerializer):
    campaign_title = serializers.CharField(source='campaign.title', read_only=True)

    class Meta:
        model = CampaignInsight
        fields = '__all__'


class InsightRecommendationSerializer(serializers.ModelSerializer):
    target_campaign_title = serializers.CharField(source='target_campaign.title', read_only=True)

    class Meta:
        model = InsightRecommendation
        fields = '__all__'


class InsightRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = InsightRun
        fields = '__all__'


class RunInsightReviewSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, allow_blank=True, default='operator-ui')


class InsightActionSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, allow_blank=True, default='operator-ui')

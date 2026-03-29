from rest_framework import serializers

from apps.autonomy_followup.models import CampaignFollowup, FollowupRecommendation, FollowupRun


class CampaignFollowupSerializer(serializers.ModelSerializer):
    campaign_title = serializers.CharField(source='campaign.title', read_only=True)

    class Meta:
        model = CampaignFollowup
        fields = '__all__'


class FollowupRecommendationSerializer(serializers.ModelSerializer):
    target_campaign_title = serializers.CharField(source='target_campaign.title', read_only=True)

    class Meta:
        model = FollowupRecommendation
        fields = '__all__'


class FollowupRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = FollowupRun
        fields = '__all__'


class RunFollowupReviewSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, allow_blank=True, default='operator-ui')


class FollowupActionSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, allow_blank=True, default='operator-ui')

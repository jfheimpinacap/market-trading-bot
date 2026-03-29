from rest_framework import serializers

from apps.autonomy_feedback.models import FeedbackRecommendation, FeedbackRun, FollowupResolution


class FollowupResolutionSerializer(serializers.ModelSerializer):
    campaign_title = serializers.CharField(source='campaign.title', read_only=True)
    followup_type = serializers.CharField(source='followup.followup_type', read_only=True)

    class Meta:
        model = FollowupResolution
        fields = '__all__'


class FeedbackRecommendationSerializer(serializers.ModelSerializer):
    target_campaign_title = serializers.CharField(source='target_campaign.title', read_only=True)

    class Meta:
        model = FeedbackRecommendation
        fields = '__all__'


class FeedbackRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeedbackRun
        fields = '__all__'


class RunFeedbackReviewSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, allow_blank=True, default='operator-ui')


class FeedbackActionSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, allow_blank=True, default='operator-ui')

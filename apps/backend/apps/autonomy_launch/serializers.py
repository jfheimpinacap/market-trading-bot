from rest_framework import serializers

from apps.autonomy_launch.models import LaunchAuthorization, LaunchReadinessSnapshot, LaunchRecommendation, LaunchRun
from apps.autonomy_scheduler.serializers import CampaignAdmissionSerializer


class LaunchReadinessSnapshotSerializer(serializers.ModelSerializer):
    campaign_title = serializers.CharField(source='campaign.title', read_only=True)

    class Meta:
        model = LaunchReadinessSnapshot
        fields = '__all__'


class LaunchAuthorizationSerializer(serializers.ModelSerializer):
    campaign_title = serializers.CharField(source='campaign.title', read_only=True)

    class Meta:
        model = LaunchAuthorization
        fields = '__all__'


class LaunchRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = LaunchRun
        fields = '__all__'


class LaunchRecommendationSerializer(serializers.ModelSerializer):
    target_campaign_title = serializers.CharField(source='target_campaign.title', read_only=True)

    class Meta:
        model = LaunchRecommendation
        fields = '__all__'


class LaunchRunPreflightSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, allow_blank=True, default='operator-ui')


class LaunchActionSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, allow_blank=True, default='operator-ui')
    rationale = serializers.CharField(required=False, allow_blank=True, default='Manual operator hold')


class LaunchCandidatesResponseSerializer(serializers.Serializer):
    candidates = CampaignAdmissionSerializer(many=True)

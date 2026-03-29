from rest_framework import serializers

from apps.autonomy_backlog.models import BacklogRecommendation, BacklogRun, GovernanceBacklogItem


class GovernanceBacklogItemSerializer(serializers.ModelSerializer):
    campaign_title = serializers.CharField(source='campaign.title', read_only=True)

    class Meta:
        model = GovernanceBacklogItem
        fields = '__all__'


class BacklogRecommendationSerializer(serializers.ModelSerializer):
    campaign_title = serializers.CharField(source='advisory_artifact.campaign.title', read_only=True)

    class Meta:
        model = BacklogRecommendation
        fields = '__all__'


class BacklogRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = BacklogRun
        fields = '__all__'


class BacklogActionSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, allow_blank=True, default='operator-ui', max_length=120)

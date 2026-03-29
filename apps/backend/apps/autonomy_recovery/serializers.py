from rest_framework import serializers

from apps.autonomy_recovery.models import RecoveryRecommendation, RecoveryRun, RecoverySnapshot


class RecoverySnapshotSerializer(serializers.ModelSerializer):
    campaign_title = serializers.CharField(source='campaign.title', read_only=True)

    class Meta:
        model = RecoverySnapshot
        fields = '__all__'


class RecoveryRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecoveryRun
        fields = '__all__'


class RecoveryRecommendationSerializer(serializers.ModelSerializer):
    target_campaign_title = serializers.CharField(source='target_campaign.title', read_only=True)

    class Meta:
        model = RecoveryRecommendation
        fields = '__all__'


class RunRecoveryReviewSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, allow_blank=True, default='operator-ui')


class RecoveryCampaignActionSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, allow_blank=True, default='operator-ui')

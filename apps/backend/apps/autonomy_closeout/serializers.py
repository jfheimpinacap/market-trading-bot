from rest_framework import serializers

from apps.autonomy_closeout.models import CampaignCloseoutReport, CloseoutFinding, CloseoutRecommendation, CloseoutRun


class CampaignCloseoutReportSerializer(serializers.ModelSerializer):
    campaign_title = serializers.CharField(source='campaign.title', read_only=True)

    class Meta:
        model = CampaignCloseoutReport
        fields = '__all__'


class CloseoutFindingSerializer(serializers.ModelSerializer):
    campaign = serializers.IntegerField(source='closeout_report.campaign_id', read_only=True)
    campaign_title = serializers.CharField(source='closeout_report.campaign.title', read_only=True)

    class Meta:
        model = CloseoutFinding
        fields = '__all__'


class CloseoutRecommendationSerializer(serializers.ModelSerializer):
    target_campaign_title = serializers.CharField(source='target_campaign.title', read_only=True)

    class Meta:
        model = CloseoutRecommendation
        fields = '__all__'


class CloseoutRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = CloseoutRun
        fields = '__all__'


class RunCloseoutReviewSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, allow_blank=True, default='operator-ui')


class CloseoutActionSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, allow_blank=True, default='operator-ui')

from rest_framework import serializers

from apps.autonomy_scheduler.models import AdmissionRecommendation, CampaignAdmission, ChangeWindow, SchedulerRun


class ChangeWindowSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChangeWindow
        fields = '__all__'


class CampaignAdmissionSerializer(serializers.ModelSerializer):
    campaign_title = serializers.CharField(source='campaign.title', read_only=True)

    class Meta:
        model = CampaignAdmission
        fields = '__all__'


class SchedulerRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchedulerRun
        fields = '__all__'


class AdmissionRecommendationSerializer(serializers.ModelSerializer):
    target_campaign_title = serializers.CharField(source='target_campaign.title', read_only=True)

    class Meta:
        model = AdmissionRecommendation
        fields = '__all__'


class SchedulerRunPlanSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, allow_blank=True, default='operator-ui')


class DeferCampaignSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, allow_blank=True, default='operator-ui')
    deferred_until = serializers.DateTimeField(required=False, allow_null=True)
    reason = serializers.CharField(required=False, allow_blank=True)


class AdmitCampaignSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, allow_blank=True, default='operator-ui')

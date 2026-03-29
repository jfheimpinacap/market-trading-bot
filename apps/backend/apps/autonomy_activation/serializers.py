from rest_framework import serializers

from apps.autonomy_activation.models import ActivationRecommendation, ActivationRun, CampaignActivation


class ActivationCandidateSerializer(serializers.Serializer):
    campaign = serializers.IntegerField(source='campaign.id')
    campaign_title = serializers.CharField(source='campaign.title')
    campaign_status = serializers.CharField(source='campaign.status')
    launch_authorization = serializers.IntegerField(source='launch_authorization.id', allow_null=True)
    authorization_status = serializers.CharField()
    expires_at = serializers.DateTimeField(allow_null=True)
    current_program_posture = serializers.CharField()
    active_window = serializers.IntegerField(source='active_window.id', allow_null=True)
    active_window_name = serializers.CharField(source='active_window.name', allow_null=True)
    domain_conflict = serializers.BooleanField()
    incident_impact = serializers.IntegerField()
    degraded_impact = serializers.IntegerField()
    rollout_pressure = serializers.IntegerField()
    dispatch_readiness_status = serializers.CharField()
    blockers = serializers.ListField(child=serializers.CharField())
    metadata = serializers.JSONField()


class CampaignActivationSerializer(serializers.ModelSerializer):
    campaign_title = serializers.CharField(source='campaign.title', read_only=True)

    class Meta:
        model = CampaignActivation
        fields = '__all__'


class ActivationRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivationRun
        fields = '__all__'


class ActivationRecommendationSerializer(serializers.ModelSerializer):
    target_campaign_title = serializers.CharField(source='target_campaign.title', read_only=True)

    class Meta:
        model = ActivationRecommendation
        fields = '__all__'


class ActivationRunDispatchReviewSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, allow_blank=True, default='operator-ui')


class ActivationDispatchSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, allow_blank=True, default='operator-ui')
    trigger_source = serializers.ChoiceField(required=False, choices=['manual_ui', 'manual_api', 'approval_resume'], default='manual_ui')
    rationale = serializers.CharField(required=False, allow_blank=True, default='Manual dispatch from activation board')

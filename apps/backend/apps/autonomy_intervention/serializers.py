from rest_framework import serializers

<<<<<<< HEAD
from apps.autonomy_intervention.models import (
    CampaignInterventionAction,
    CampaignInterventionRequest,
    InterventionOutcome,
    InterventionRun,
)
=======
from apps.autonomy_intervention.models import CampaignInterventionAction, CampaignInterventionRequest, InterventionOutcome
>>>>>>> origin/main


class CampaignInterventionRequestSerializer(serializers.ModelSerializer):
    campaign_title = serializers.CharField(source='campaign.title', read_only=True)

    class Meta:
        model = CampaignInterventionRequest
        fields = '__all__'


class CampaignInterventionActionSerializer(serializers.ModelSerializer):
    campaign_title = serializers.CharField(source='campaign.title', read_only=True)

    class Meta:
        model = CampaignInterventionAction
        fields = '__all__'


class InterventionOutcomeSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterventionOutcome
        fields = '__all__'


<<<<<<< HEAD
class InterventionRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterventionRun
        fields = '__all__'


class RunInterventionReviewSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, allow_blank=True, default='operator-ui')


class CreateInterventionRequestSerializer(serializers.Serializer):
    source_type = serializers.ChoiceField(choices=[
        'operations_recommendation',
        'attention_signal',
        'manual',
        'incident_response',
    ], default='manual')
    requested_action = serializers.ChoiceField(choices=['PAUSE_CAMPAIGN', 'RESUME_CAMPAIGN', 'ESCALATE_TO_APPROVAL', 'REVIEW_FOR_ABORT', 'CLEAR_TO_CONTINUE'])
    severity = serializers.CharField(required=False, allow_blank=True, default='MEDIUM')
    rationale = serializers.CharField(required=False, allow_blank=True, default='Manual intervention request')
    reason_codes = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    blockers = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    linked_signal_id = serializers.IntegerField(required=False)
    linked_recommendation_id = serializers.IntegerField(required=False)
    requested_by = serializers.CharField(required=False, allow_blank=True, default='operator-ui')
    metadata = serializers.JSONField(required=False, default=dict)


class ExecuteInterventionRequestSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, allow_blank=True, default='operator-ui')
    rationale = serializers.CharField(required=False, allow_blank=True, default='Manual intervention execution')
    metadata = serializers.JSONField(required=False, default=dict)
=======
class CreateInterventionRequestSerializer(serializers.Serializer):
    source_type = serializers.ChoiceField(choices=[x for x, _ in CampaignInterventionRequest._meta.get_field('source_type').choices], required=False)
    requested_action = serializers.ChoiceField(choices=[x for x, _ in CampaignInterventionRequest._meta.get_field('requested_action').choices])
    severity = serializers.CharField(required=False, allow_blank=True)
    rationale = serializers.CharField(required=False, allow_blank=True)
    reason_codes = serializers.JSONField(required=False)
    blockers = serializers.JSONField(required=False)
    linked_signal_id = serializers.IntegerField(required=False)
    linked_recommendation_id = serializers.IntegerField(required=False)
    requested_by = serializers.CharField(required=False, allow_blank=True)
    metadata = serializers.JSONField(required=False)


class ExecuteInterventionSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, allow_blank=True, default='operator-ui')


class RunReviewSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, allow_blank=True, default='operator-ui')
>>>>>>> origin/main

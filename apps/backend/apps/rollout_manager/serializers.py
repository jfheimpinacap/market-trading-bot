from rest_framework import serializers

from apps.champion_challenger.serializers import StackProfileBindingSerializer
from apps.rollout_manager.models import RolloutDecision, RolloutGuardrailEvent, StackRolloutPlan, StackRolloutRun


class RolloutGuardrailEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = RolloutGuardrailEvent
        fields = '__all__'


class RolloutDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RolloutDecision
        fields = '__all__'


class StackRolloutPlanSerializer(serializers.ModelSerializer):
    champion_binding = StackProfileBindingSerializer(read_only=True)
    candidate_binding = StackProfileBindingSerializer(read_only=True)

    class Meta:
        model = StackRolloutPlan
        fields = '__all__'


class StackRolloutRunSerializer(serializers.ModelSerializer):
    plan = StackRolloutPlanSerializer(read_only=True)
    guardrail_events = RolloutGuardrailEventSerializer(read_only=True, many=True)
    decisions = RolloutDecisionSerializer(read_only=True, many=True)

    class Meta:
        model = StackRolloutRun
        fields = '__all__'


class CreateRolloutPlanRequestSerializer(serializers.Serializer):
    candidate_binding_id = serializers.IntegerField(required=False, min_value=1)
    source_review_run_id = serializers.IntegerField(required=False, min_value=1)
    mode = serializers.ChoiceField(choices=['SHADOW_ONLY', 'CANARY', 'STAGED'], default='CANARY', required=False)
    canary_percentage = serializers.IntegerField(required=False, min_value=0, max_value=100, default=10)
    sampling_rule = serializers.CharField(required=False, default='MARKET_HASH')
    profile_scope = serializers.CharField(required=False, allow_blank=True)
    guardrails = serializers.DictField(required=False)
    summary = serializers.CharField(required=False, allow_blank=True)
    metadata = serializers.DictField(required=False)


class StartRolloutRunRequestSerializer(serializers.Serializer):
    metadata = serializers.DictField(required=False)


class RolloutControlRequestSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, default='operator')
    reason = serializers.CharField(required=False, allow_blank=True, default='')


class RolloutDecisionEvaluationRequestSerializer(serializers.Serializer):
    metrics = serializers.DictField(required=False)

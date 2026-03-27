from rest_framework import serializers

from apps.automation_policy.models import AutomationActionLog, AutomationDecision, AutomationPolicyProfile, AutomationPolicyRule


class AutomationPolicyRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutomationPolicyRule
        fields = '__all__'


class AutomationPolicyProfileSerializer(serializers.ModelSerializer):
    rules = AutomationPolicyRuleSerializer(many=True, read_only=True)

    class Meta:
        model = AutomationPolicyProfile
        fields = '__all__'


class AutomationDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutomationDecision
        fields = '__all__'


class AutomationActionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutomationActionLog
        fields = '__all__'


class AutomationEvaluateRequestSerializer(serializers.Serializer):
    action_type = serializers.CharField(max_length=80)
    source_context_type = serializers.CharField(max_length=80, required=False, allow_blank=True)
    runbook_instance_id = serializers.IntegerField(required=False)
    runbook_step_id = serializers.IntegerField(required=False)
    metadata = serializers.JSONField(required=False)
    execute = serializers.BooleanField(required=False, default=False)


class AutomationApplyProfileSerializer(serializers.Serializer):
    profile_slug = serializers.SlugField(max_length=80)

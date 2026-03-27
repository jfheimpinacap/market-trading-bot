from rest_framework import serializers

from apps.go_live_gate.models import CapitalFirewallRule, GoLiveApprovalRequest, GoLiveChecklistRun, GoLiveRehearsalRun


class CapitalFirewallRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = CapitalFirewallRule
        fields = '__all__'


class GoLiveChecklistRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoLiveChecklistRun
        fields = '__all__'


class GoLiveApprovalRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoLiveApprovalRequest
        fields = '__all__'


class GoLiveRehearsalRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoLiveRehearsalRun
        fields = '__all__'


class RunGoLiveChecklistRequestSerializer(serializers.Serializer):
    requested_by = serializers.CharField(required=False, default='local-operator')
    context = serializers.CharField(required=False, default='manual')
    manual_inputs = serializers.DictField(required=False)
    metadata = serializers.DictField(required=False)


class CreateGoLiveApprovalRequestSerializer(serializers.Serializer):
    requested_by = serializers.CharField()
    rationale = serializers.CharField(required=False, allow_blank=True)
    scope = serializers.CharField(required=False, default='global')
    requested_mode = serializers.CharField(required=False, default='PRELIVE_REHEARSAL')
    blocking_reasons = serializers.ListField(child=serializers.CharField(), required=False)
    checklist_run_id = serializers.IntegerField(required=False)
    metadata = serializers.DictField(required=False)


class RunGoLiveRehearsalRequestSerializer(serializers.Serializer):
    intent_id = serializers.IntegerField()
    requested_by = serializers.CharField(required=False, default='local-operator')
    metadata = serializers.DictField(required=False)

from rest_framework import serializers

from apps.profile_manager.models import ManagedProfileBinding, ProfileDecision, ProfileGovernanceRun


class ManagedProfileBindingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ManagedProfileBinding
        fields = ('id', 'module_key', 'operating_mode', 'profile_slug', 'profile_label', 'is_active', 'metadata', 'created_at', 'updated_at')
        read_only_fields = fields


class ProfileDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfileDecision
        fields = (
            'id',
            'decision_mode',
            'target_research_profile',
            'target_signal_profile',
            'target_opportunity_supervisor_profile',
            'target_mission_control_profile',
            'target_portfolio_governor_profile',
            'target_prediction_profile',
            'rationale',
            'reason_codes',
            'blocking_constraints',
            'metadata',
            'is_applied',
            'applied_at',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class ProfileGovernanceRunSerializer(serializers.ModelSerializer):
    decision = ProfileDecisionSerializer(read_only=True)

    class Meta:
        model = ProfileGovernanceRun
        fields = (
            'id',
            'status',
            'regime',
            'runtime_mode',
            'readiness_status',
            'safety_status',
            'triggered_by',
            'started_at',
            'finished_at',
            'summary',
            'details',
            'decision',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class RunProfileGovernanceSerializer(serializers.Serializer):
    decision_mode = serializers.ChoiceField(choices=['RECOMMEND_ONLY', 'APPLY_SAFE', 'APPLY_FORCED'], required=False)
    triggered_by = serializers.CharField(required=False, allow_blank=False, max_length=64)


class ProfileGovernanceSummarySerializer(serializers.Serializer):
    latest_run = serializers.IntegerField(allow_null=True)
    current_regime = serializers.CharField()
    decision_mode = serializers.CharField(allow_blank=True)
    is_applied = serializers.BooleanField()
    target_profiles = serializers.DictField(child=serializers.CharField(allow_blank=True))
    blocking_constraints = serializers.ListField(child=serializers.CharField())
    reason_codes = serializers.ListField(child=serializers.CharField())
    runtime_mode = serializers.CharField()
    readiness_status = serializers.CharField()
    safety_status = serializers.CharField()
    available_bindings = ManagedProfileBindingSerializer(many=True)
    paper_demo_only = serializers.BooleanField()
    real_execution_enabled = serializers.BooleanField()

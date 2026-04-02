from rest_framework import serializers

from apps.runtime_governor.models import (
    GlobalOperatingModeDecision,
    GlobalOperatingModeRecommendation,
    GlobalOperatingModeSwitchRecord,
    GlobalRuntimePostureRun,
    GlobalRuntimePostureSnapshot,
    GlobalModeEnforcementRun,
    GlobalModeModuleImpact,
    GlobalModeEnforcementDecision,
    GlobalModeEnforcementRecommendation,
    RuntimeMode,
    RuntimeModeProfile,
    RuntimeModeState,
    RuntimeTransitionLog,
)


class RuntimeModeProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = RuntimeModeProfile
        fields = '__all__'


class RuntimeModeStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RuntimeModeState
        fields = '__all__'


class RuntimeTransitionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = RuntimeTransitionLog
        fields = '__all__'


class RuntimeSetModeSerializer(serializers.Serializer):
    mode = serializers.ChoiceField(choices=RuntimeMode.choices)
    rationale = serializers.CharField(required=False, allow_blank=True, max_length=255)
    set_by = serializers.CharField(required=False, allow_blank=True, default='operator')
    metadata = serializers.JSONField(required=False)


class RunOperatingModeReviewSerializer(serializers.Serializer):
    triggered_by = serializers.CharField(required=False, allow_blank=True, default='operator-ui')
    auto_apply = serializers.BooleanField(required=False, default=True)


class GlobalRuntimePostureRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlobalRuntimePostureRun
        fields = '__all__'


class GlobalRuntimePostureSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlobalRuntimePostureSnapshot
        fields = '__all__'


class GlobalOperatingModeDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlobalOperatingModeDecision
        fields = '__all__'


class GlobalOperatingModeSwitchRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlobalOperatingModeSwitchRecord
        fields = '__all__'


class GlobalOperatingModeRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlobalOperatingModeRecommendation
        fields = '__all__'


class RunModeEnforcementReviewSerializer(serializers.Serializer):
    triggered_by = serializers.CharField(required=False, allow_blank=True, default='operator-ui')


class GlobalModeEnforcementRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlobalModeEnforcementRun
        fields = '__all__'


class GlobalModeModuleImpactSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlobalModeModuleImpact
        fields = '__all__'


class GlobalModeEnforcementDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlobalModeEnforcementDecision
        fields = '__all__'


class GlobalModeEnforcementRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlobalModeEnforcementRecommendation
        fields = '__all__'

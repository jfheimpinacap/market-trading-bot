from rest_framework import serializers

from apps.runtime_governor.models import RuntimeMode, RuntimeModeProfile, RuntimeModeState, RuntimeTransitionLog


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

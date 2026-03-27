from rest_framework import serializers

from apps.incident_commander.models import DegradedModeState, IncidentAction, IncidentRecord, IncidentRecoveryRun


class IncidentActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = IncidentAction
        fields = '__all__'


class IncidentRecoveryRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = IncidentRecoveryRun
        fields = '__all__'


class IncidentRecordSerializer(serializers.ModelSerializer):
    actions = IncidentActionSerializer(many=True, read_only=True)
    recovery_runs = IncidentRecoveryRunSerializer(many=True, read_only=True)

    class Meta:
        model = IncidentRecord
        fields = '__all__'


class DegradedModeStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DegradedModeState
        fields = '__all__'

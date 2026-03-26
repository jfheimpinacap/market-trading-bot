from rest_framework import serializers

from apps.mission_control.models import MissionControlCycle, MissionControlSession, MissionControlState, MissionControlStep


class MissionControlStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = MissionControlStep
        fields = ['id', 'cycle', 'step_type', 'status', 'started_at', 'finished_at', 'summary', 'details', 'created_at']


class MissionControlCycleSerializer(serializers.ModelSerializer):
    steps = MissionControlStepSerializer(many=True, read_only=True)

    class Meta:
        model = MissionControlCycle
        fields = [
            'id', 'session', 'cycle_number', 'status', 'started_at', 'finished_at', 'steps_run_count',
            'opportunities_built', 'proposals_generated', 'queue_count', 'auto_execute_count', 'blocked_count',
            'summary', 'details', 'created_at', 'steps',
        ]


class MissionControlSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MissionControlSession
        fields = ['id', 'status', 'started_at', 'finished_at', 'cycle_count', 'last_cycle_at', 'summary', 'metadata', 'created_at', 'updated_at']


class MissionControlStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MissionControlState
        fields = [
            'id', 'status', 'active_session', 'pause_requested', 'stop_requested', 'cycle_in_progress',
            'last_heartbeat_at', 'last_error', 'profile_slug', 'settings_snapshot', 'updated_at',
        ]


class MissionControlStartSerializer(serializers.Serializer):
    profile_slug = serializers.CharField(required=False, allow_blank=True)
    cycle_interval_seconds = serializers.IntegerField(required=False, min_value=5)
    max_cycles_per_session = serializers.IntegerField(required=False, min_value=1)

from rest_framework import serializers

from apps.mission_control.models import (
    AutonomousCadenceDecision,
    AutonomousHeartbeatDecision,
    AutonomousHeartbeatRecommendation,
    AutonomousHeartbeatRun,
    AutonomousMissionCycleExecution,
    AutonomousMissionCycleOutcome,
    AutonomousMissionCyclePlan,
    AutonomousMissionRuntimeRecommendation,
    AutonomousMissionRuntimeRun,
    AutonomousRunnerState,
    AutonomousRuntimeSession,
    AutonomousRuntimeTick,
    AutonomousSessionRecommendation,
    AutonomousTickDispatchAttempt,
    MissionControlCycle,
    MissionControlSession,
    MissionControlState,
    MissionControlStep,
)


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


class AutonomousRuntimeRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomousMissionRuntimeRun
        fields = '__all__'


class AutonomousCyclePlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomousMissionCyclePlan
        fields = '__all__'


class AutonomousCycleExecutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomousMissionCycleExecution
        fields = '__all__'


class AutonomousCycleOutcomeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomousMissionCycleOutcome
        fields = '__all__'


class AutonomousRuntimeRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomousMissionRuntimeRecommendation
        fields = '__all__'


class AutonomousRuntimeRunRequestSerializer(serializers.Serializer):
    cycle_count = serializers.IntegerField(required=False, min_value=1, max_value=20, default=1)
    profile_slug = serializers.CharField(required=False, allow_blank=True)


class AutonomousRuntimeSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomousRuntimeSession
        fields = '__all__'


class AutonomousRuntimeTickSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomousRuntimeTick
        fields = '__all__'


class AutonomousCadenceDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomousCadenceDecision
        fields = '__all__'


class AutonomousSessionRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomousSessionRecommendation
        fields = '__all__'


class AutonomousSessionStartRequestSerializer(serializers.Serializer):
    profile_slug = serializers.CharField(required=False, allow_blank=True)
    runtime_mode = serializers.CharField(required=False, allow_blank=True)


class AutonomousRunnerStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomousRunnerState
        fields = '__all__'


class AutonomousHeartbeatRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomousHeartbeatRun
        fields = '__all__'


class AutonomousHeartbeatDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomousHeartbeatDecision
        fields = '__all__'


class AutonomousTickDispatchAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomousTickDispatchAttempt
        fields = '__all__'


class AutonomousHeartbeatRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomousHeartbeatRecommendation
        fields = '__all__'

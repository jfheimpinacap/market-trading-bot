from rest_framework import serializers

from apps.execution_simulator.models import ExecutionPolicyProfile
from apps.replay_lab.models import ReplayRun, ReplaySourceScope, ReplayStep
from apps.replay_lab.services.execution_replay import REPLAY_EXECUTION_MODE_AWARE, REPLAY_EXECUTION_MODE_NAIVE


class ReplayStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReplayStep
        fields = '__all__'


class ReplayRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReplayRun
        fields = '__all__'


class ReplayRunRequestSerializer(serializers.Serializer):
    provider_scope = serializers.CharField(required=False, default='all')
    source_scope = serializers.ChoiceField(choices=ReplaySourceScope.choices, required=False, default=ReplaySourceScope.REAL_ONLY)
    start_timestamp = serializers.DateTimeField()
    end_timestamp = serializers.DateTimeField()
    market_limit = serializers.IntegerField(required=False, min_value=1, max_value=100, default=8)
    active_only = serializers.BooleanField(required=False, default=True)
    use_allocation = serializers.BooleanField(required=False, default=True)
    use_learning_adjustments = serializers.BooleanField(required=False, default=True)
    auto_execute_allowed = serializers.BooleanField(required=False, default=True)
    treat_approval_required_as_skip = serializers.BooleanField(required=False, default=True)
    snapshot_sampling_interval = serializers.IntegerField(required=False, min_value=1, max_value=1440, allow_null=True)
    stop_on_error = serializers.BooleanField(required=False, default=False)
    execution_mode = serializers.ChoiceField(
        required=False,
        choices=[REPLAY_EXECUTION_MODE_NAIVE, REPLAY_EXECUTION_MODE_AWARE],
        default=REPLAY_EXECUTION_MODE_NAIVE,
    )
    execution_profile = serializers.ChoiceField(
        required=False,
        choices=ExecutionPolicyProfile.choices,
        default=ExecutionPolicyProfile.BALANCED,
    )

    def validate(self, attrs):
        if attrs['start_timestamp'] >= attrs['end_timestamp']:
            raise serializers.ValidationError('start_timestamp must be earlier than end_timestamp.')
        return attrs

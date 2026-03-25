from rest_framework import serializers

from apps.experiment_lab.models import ExperimentRun, ExperimentRunType, StrategyProfile


class StrategyProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = StrategyProfile
        fields = '__all__'


class ExperimentRunSerializer(serializers.ModelSerializer):
    strategy_profile = StrategyProfileSerializer(read_only=True)

    class Meta:
        model = ExperimentRun
        fields = '__all__'


class ExperimentRunRequestSerializer(serializers.Serializer):
    strategy_profile_id = serializers.IntegerField(min_value=1)
    run_type = serializers.ChoiceField(choices=ExperimentRunType.choices)
    provider_scope = serializers.CharField(required=False, default='all')
    start_timestamp = serializers.DateTimeField(required=False)
    end_timestamp = serializers.DateTimeField(required=False)
    active_only = serializers.BooleanField(required=False, default=True)
    use_allocation = serializers.BooleanField(required=False, default=True)
    stop_on_error = serializers.BooleanField(required=False, default=False)
    related_continuous_session_id = serializers.IntegerField(required=False, min_value=1)

    def validate(self, attrs):
        start = attrs.get('start_timestamp')
        end = attrs.get('end_timestamp')
        if start and end and start >= end:
            raise serializers.ValidationError('start_timestamp must be earlier than end_timestamp.')
        return attrs

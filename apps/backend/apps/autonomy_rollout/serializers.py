from rest_framework import serializers

from apps.autonomy_rollout.models import (
    AutonomyBaselineSnapshot,
    AutonomyPostChangeSnapshot,
    AutonomyRolloutRecommendation,
    AutonomyRolloutRun,
)


class AutonomyBaselineSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomyBaselineSnapshot
        fields = '__all__'


class AutonomyPostChangeSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomyPostChangeSnapshot
        fields = '__all__'


class AutonomyRolloutRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomyRolloutRecommendation
        fields = '__all__'


class AutonomyRolloutRunSerializer(serializers.ModelSerializer):
    baseline_snapshot = AutonomyBaselineSnapshotSerializer(read_only=True)
    post_change_snapshot = AutonomyPostChangeSnapshotSerializer(read_only=True)
    recommendations = AutonomyRolloutRecommendationSerializer(many=True, read_only=True)

    class Meta:
        model = AutonomyRolloutRun
        fields = '__all__'


class StartAutonomyRolloutSerializer(serializers.Serializer):
    autonomy_stage_transition_id = serializers.IntegerField(min_value=1)
    observation_window_days = serializers.IntegerField(required=False, min_value=1, max_value=90, default=14)
    metadata = serializers.JSONField(required=False)


class RolloutEvaluationSerializer(serializers.Serializer):
    metadata = serializers.JSONField(required=False)


class RollbackAutonomyRolloutSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=False, default='Manual operator rollback of autonomy stage transition.')
    require_approval = serializers.BooleanField(required=False, default=True)

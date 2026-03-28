from rest_framework import serializers

from apps.policy_rollout.models import PolicyBaselineSnapshot, PolicyPostChangeSnapshot, PolicyRolloutRecommendation, PolicyRolloutRun


class PolicyBaselineSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = PolicyBaselineSnapshot
        fields = '__all__'


class PolicyPostChangeSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = PolicyPostChangeSnapshot
        fields = '__all__'


class PolicyRolloutRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PolicyRolloutRecommendation
        fields = '__all__'


class PolicyRolloutRunSerializer(serializers.ModelSerializer):
    baseline_snapshot = PolicyBaselineSnapshotSerializer(read_only=True)
    post_change_snapshot = PolicyPostChangeSnapshotSerializer(read_only=True)
    recommendations = PolicyRolloutRecommendationSerializer(many=True, read_only=True)

    class Meta:
        model = PolicyRolloutRun
        fields = '__all__'


class StartPolicyRolloutSerializer(serializers.Serializer):
    policy_tuning_candidate_id = serializers.IntegerField(min_value=1)
    application_log_id = serializers.IntegerField(required=False, min_value=1)
    observation_window_days = serializers.IntegerField(required=False, min_value=1, max_value=90, default=14)
    metadata = serializers.JSONField(required=False)


class RolloutEvaluationSerializer(serializers.Serializer):
    metadata = serializers.JSONField(required=False)


class RollbackPolicyRolloutSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=False, default='Manual operator rollback.')
    require_approval = serializers.BooleanField(required=False, default=True)

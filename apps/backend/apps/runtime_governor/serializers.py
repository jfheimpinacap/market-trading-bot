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
    RuntimeFeedbackDecision,
    RuntimeFeedbackApplyDecision,
    RuntimeFeedbackApplyRecommendation,
    RuntimeFeedbackApplyRecord,
    RuntimeFeedbackApplyRun,
    RuntimeModeStabilizationRecommendation,
    RuntimeModeStabilizationRun,
    RuntimeModeStabilityReview,
    RuntimeModeTransitionApplyRecord,
    RuntimeModeTransitionDecision,
    RuntimeModeTransitionSnapshot,
    RuntimeFeedbackRecommendation,
    RuntimeFeedbackRun,
    RuntimePerformanceSnapshot,
    RuntimeDiagnosticReview,
    RuntimeTuningContextSnapshot,
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


class RunRuntimeFeedbackReviewSerializer(serializers.Serializer):
    triggered_by = serializers.CharField(required=False, allow_blank=True, default='operator-ui')
    auto_apply = serializers.BooleanField(required=False, default=False)


class RuntimeFeedbackRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = RuntimeFeedbackRun
        fields = '__all__'


class RuntimePerformanceSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = RuntimePerformanceSnapshot
        fields = '__all__'


class RuntimeDiagnosticReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = RuntimeDiagnosticReview
        fields = '__all__'


class RuntimeFeedbackDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RuntimeFeedbackDecision
        fields = '__all__'


class RuntimeFeedbackRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = RuntimeFeedbackRecommendation
        fields = '__all__'


class RunRuntimeFeedbackApplyReviewSerializer(serializers.Serializer):
    triggered_by = serializers.CharField(required=False, allow_blank=True, default='operator-ui')
    auto_apply = serializers.BooleanField(required=False, default=False)


class RunModeStabilizationReviewSerializer(serializers.Serializer):
    triggered_by = serializers.CharField(required=False, allow_blank=True, default='operator-ui')
    auto_apply_safe = serializers.BooleanField(required=False, default=False)


class RuntimeModeStabilizationRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = RuntimeModeStabilizationRun
        fields = '__all__'


class RuntimeModeTransitionSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = RuntimeModeTransitionSnapshot
        fields = '__all__'


class RuntimeModeStabilityReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = RuntimeModeStabilityReview
        fields = '__all__'


class RuntimeModeTransitionDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RuntimeModeTransitionDecision
        fields = '__all__'


class RuntimeModeStabilizationRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = RuntimeModeStabilizationRecommendation
        fields = '__all__'


class RuntimeModeTransitionApplyRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = RuntimeModeTransitionApplyRecord
        fields = '__all__'


class RuntimeFeedbackApplyRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = RuntimeFeedbackApplyRun
        fields = '__all__'


class RuntimeFeedbackApplyDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RuntimeFeedbackApplyDecision
        fields = '__all__'


class RuntimeFeedbackApplyRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = RuntimeFeedbackApplyRecord
        fields = '__all__'


class RuntimeTuningContextSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = RuntimeTuningContextSnapshot
        fields = '__all__'


class RuntimeTuningContextDriftSummarySerializer(serializers.Serializer):
    total_snapshots = serializers.IntegerField()
    status_counts = serializers.DictField(child=serializers.IntegerField())
    latest_by_scope = serializers.DictField()


class RuntimeTuningContextDiffSerializer(serializers.Serializer):
    source_scope = serializers.CharField()
    current_snapshot_id = serializers.IntegerField()
    previous_snapshot_id = serializers.IntegerField(allow_null=True)
    drift_status = serializers.CharField()
    changed_fields = serializers.JSONField()
    unchanged_fields = serializers.JSONField(required=False)
    diff_summary = serializers.CharField()
    created_at = serializers.DateTimeField(required=False, allow_null=True)


class RuntimeTuningRunCorrelationSerializer(serializers.Serializer):
    source_scope = serializers.CharField()
    source_run_id = serializers.IntegerField(allow_null=True)
    tuning_snapshot_id = serializers.IntegerField()
    tuning_profile_name = serializers.CharField()
    tuning_profile_fingerprint = serializers.CharField()
    drift_status = serializers.CharField()
    run_created_at = serializers.DateTimeField(required=False, allow_null=True)
    correlation_summary = serializers.CharField()


class RuntimeTuningScopeDigestSerializer(serializers.Serializer):
    source_scope = serializers.CharField()
    latest_snapshot_id = serializers.IntegerField()
    latest_run_id = serializers.IntegerField(allow_null=True)
    tuning_profile_name = serializers.CharField()
    tuning_profile_fingerprint = serializers.CharField()
    latest_drift_status = serializers.CharField()
    latest_snapshot_created_at = serializers.DateTimeField()
    digest_summary = serializers.CharField()
    latest_diff_snapshot_id = serializers.IntegerField(allow_null=True)
    latest_diff_status = serializers.CharField(allow_null=True)
    latest_diff_summary = serializers.CharField(allow_null=True)


class RuntimeTuningChangeAlertSerializer(serializers.Serializer):
    source_scope = serializers.CharField()
    latest_snapshot_id = serializers.IntegerField()
    tuning_profile_name = serializers.CharField()
    tuning_profile_fingerprint = serializers.CharField()
    latest_drift_status = serializers.CharField()
    latest_diff_snapshot_id = serializers.IntegerField(allow_null=True)
    latest_diff_status = serializers.CharField(allow_null=True)
    latest_diff_summary = serializers.CharField(allow_null=True)
    alert_status = serializers.CharField()
    alert_summary = serializers.CharField()
    created_at = serializers.DateTimeField(required=False, allow_null=True)


class RuntimeTuningAlertSummarySerializer(serializers.Serializer):
    total_scope_count = serializers.IntegerField()
    stable_count = serializers.IntegerField()
    minor_change_count = serializers.IntegerField()
    profile_shift_count = serializers.IntegerField()
    review_now_count = serializers.IntegerField()
    highest_priority_scope = serializers.CharField(required=False, allow_null=True)
    most_recent_changed_scope = serializers.CharField(required=False, allow_null=True)
    ordered_scopes = serializers.JSONField()
    summary = serializers.CharField()


class RuntimeTuningReviewBoardRowSerializer(serializers.Serializer):
    source_scope = serializers.CharField()
    alert_status = serializers.CharField()
    drift_status = serializers.CharField()
    attention_priority = serializers.CharField()
    attention_rank = serializers.IntegerField()
    latest_diff_snapshot_id = serializers.IntegerField(allow_null=True)
    latest_diff_status = serializers.CharField(allow_null=True)
    latest_diff_summary = serializers.CharField(allow_null=True)
    correlated_run_id = serializers.IntegerField(allow_null=True)
    correlated_run_timestamp = serializers.DateTimeField(required=False, allow_null=True)
    correlated_profile_name = serializers.CharField(allow_null=True)
    correlated_profile_fingerprint = serializers.CharField(allow_null=True)
    changed_field_count = serializers.IntegerField()
    changed_guardrail_count = serializers.IntegerField()
    review_reason_codes = serializers.ListField(child=serializers.CharField())
    recommended_next_action = serializers.CharField()
    board_summary = serializers.CharField()


class RuntimeFeedbackApplyRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = RuntimeFeedbackApplyRecommendation
        fields = '__all__'


class RuntimeTuningProfileSummarySerializer(serializers.Serializer):
    profile_name = serializers.CharField()
    backlog_thresholds = serializers.JSONField()
    backlog_weights = serializers.JSONField()
    feedback_guardrails = serializers.JSONField()
    operating_mode_guardrails = serializers.JSONField()
    stabilization_guardrails = serializers.JSONField()
    effective_values = serializers.JSONField()
    summary = serializers.CharField()
    created_at = serializers.DateTimeField(required=False, allow_null=True)


class RuntimeTuningProfileValuesSerializer(serializers.Serializer):
    profile_name = serializers.CharField()
    profile_values = serializers.JSONField()

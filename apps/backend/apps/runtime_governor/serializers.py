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
    RuntimeTuningReviewAction,
    RuntimeTuningReviewState,
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
    review_status = serializers.CharField()
    review_summary = serializers.CharField()
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


class RuntimeTuningInvestigationPacketSerializer(serializers.Serializer):
    source_scope = serializers.CharField()
    attention_priority = serializers.CharField()
    attention_rank = serializers.IntegerField()
    alert_status = serializers.CharField()
    drift_status = serializers.CharField()
    board_summary = serializers.CharField()
    review_reason_codes = serializers.ListField(child=serializers.CharField())
    recommended_next_action = serializers.CharField()
    investigation_summary = serializers.CharField()

    latest_diff_snapshot_id = serializers.IntegerField(allow_null=True)
    latest_diff_status = serializers.CharField(allow_null=True)
    latest_diff_summary = serializers.CharField(allow_null=True)
    changed_field_count = serializers.IntegerField()
    changed_guardrail_count = serializers.IntegerField()
    changed_fields_preview = serializers.ListField(child=serializers.CharField())
    changed_guardrail_fields_preview = serializers.ListField(child=serializers.CharField())
    changed_fields_remaining_count = serializers.IntegerField()
    changed_guardrail_remaining_count = serializers.IntegerField()

    correlated_run_id = serializers.IntegerField(allow_null=True)
    correlated_run_timestamp = serializers.DateTimeField(required=False, allow_null=True)
    correlated_profile_name = serializers.CharField(allow_null=True)
    correlated_profile_fingerprint = serializers.CharField(allow_null=True)
    correlated_run_summary = serializers.CharField(allow_null=True)

    latest_snapshot_id = serializers.IntegerField()
    latest_snapshot_created_at = serializers.DateTimeField()
    previous_snapshot_id = serializers.IntegerField(allow_null=True)
    has_comparable_diff = serializers.BooleanField()
    has_correlated_run = serializers.BooleanField()

    runtime_deep_link = serializers.CharField()
    runtime_diff_deep_link = serializers.CharField()




class RuntimeTuningScopeTimelineEntrySerializer(serializers.Serializer):
    snapshot_id = serializers.IntegerField()
    created_at = serializers.DateTimeField()
    drift_status = serializers.CharField()
    alert_status = serializers.CharField()
    profile_name = serializers.CharField()
    profile_fingerprint = serializers.CharField(allow_null=True)
    diff_summary = serializers.CharField()
    has_comparable_diff = serializers.BooleanField()
    changed_field_count = serializers.IntegerField()
    changed_guardrail_count = serializers.IntegerField()
    correlated_run_id = serializers.IntegerField(allow_null=True)
    correlated_run_timestamp = serializers.DateTimeField(required=False, allow_null=True)
    timeline_reason_codes = serializers.ListField(child=serializers.CharField())
    timeline_label = serializers.CharField()


class RuntimeTuningScopeTimelineSerializer(serializers.Serializer):
    source_scope = serializers.CharField()
    entry_count = serializers.IntegerField()
    latest_snapshot_id = serializers.IntegerField()
    latest_snapshot_created_at = serializers.DateTimeField()
    timeline_summary = serializers.CharField()
    is_recently_stable = serializers.BooleanField()
    has_recent_profile_shift = serializers.BooleanField()
    has_recent_review_now = serializers.BooleanField()
    entries = RuntimeTuningScopeTimelineEntrySerializer(many=True)

class RuntimeTuningCockpitPanelItemSerializer(serializers.Serializer):
    source_scope = serializers.CharField()
    attention_priority = serializers.CharField()
    attention_rank = serializers.IntegerField()
    alert_status = serializers.CharField()
    drift_status = serializers.CharField()
    board_summary = serializers.CharField()
    recommended_next_action = serializers.CharField()
    latest_diff_snapshot_id = serializers.IntegerField(allow_null=True)
    latest_diff_status = serializers.CharField(allow_null=True)
    latest_diff_summary = serializers.CharField(allow_null=True)
    correlated_run_id = serializers.IntegerField(allow_null=True)
    correlated_run_timestamp = serializers.DateTimeField(required=False, allow_null=True)
    correlated_profile_name = serializers.CharField(allow_null=True)
    correlated_profile_fingerprint = serializers.CharField(allow_null=True)
    runtime_deep_link = serializers.CharField()


class RuntimeTuningCockpitPanelSerializer(serializers.Serializer):
    generated_at = serializers.DateTimeField()
    total_scope_count = serializers.IntegerField()
    attention_scope_count = serializers.IntegerField()
    highest_priority_scope = serializers.CharField(required=False, allow_null=True)
    highest_priority_status = serializers.CharField(required=False, allow_null=True)
    panel_summary = serializers.CharField()
    items = RuntimeTuningCockpitPanelItemSerializer(many=True)


class RuntimeTuningCockpitPanelDetailSerializer(RuntimeTuningCockpitPanelItemSerializer):
    review_reason_codes = serializers.ListField(child=serializers.CharField())
    changed_field_count = serializers.IntegerField()
    changed_guardrail_count = serializers.IntegerField()




class RuntimeTuningReviewQueueItemSerializer(serializers.Serializer):
    source_scope = serializers.CharField()
    effective_review_status = serializers.CharField()
    attention_priority = serializers.CharField()
    queue_rank = serializers.IntegerField()
    requires_manual_attention = serializers.BooleanField()
    queue_reason_codes = serializers.ListField(child=serializers.CharField())
    technical_summary = serializers.CharField()
    review_summary = serializers.CharField()
    last_action_type = serializers.CharField(allow_blank=True)
    last_action_at = serializers.DateTimeField(required=False, allow_null=True)
    has_newer_snapshot_than_reviewed = serializers.BooleanField()
    runtime_deep_link = serializers.CharField()
    runtime_investigation_deep_link = serializers.CharField()
    latest_snapshot_id = serializers.IntegerField(allow_null=True, required=False)
    last_reviewed_snapshot_id = serializers.IntegerField(allow_null=True, required=False)


class RuntimeTuningReviewQueueSerializer(serializers.Serializer):
    total_scope_count = serializers.IntegerField()
    queue_count = serializers.IntegerField()
    unreviewed_count = serializers.IntegerField()
    followup_count = serializers.IntegerField()
    stale_count = serializers.IntegerField()
    highest_priority_scope = serializers.CharField(required=False, allow_null=True)
    queue_summary = serializers.CharField()
    items = RuntimeTuningReviewQueueItemSerializer(many=True)


class RuntimeTuningReviewQueueDetailSerializer(RuntimeTuningReviewQueueItemSerializer):
    stored_review_status = serializers.CharField(required=False)
    queue_summary = serializers.CharField()


class RuntimeTuningReviewAgingItemSerializer(RuntimeTuningReviewQueueItemSerializer):
    age_bucket = serializers.CharField()
    age_days = serializers.IntegerField()
    overdue = serializers.BooleanField()
    aging_rank = serializers.IntegerField()
    aging_reason_codes = serializers.ListField(child=serializers.CharField())
    age_reference_timestamp = serializers.DateTimeField(required=False, allow_null=True)


class RuntimeTuningReviewAgingSerializer(serializers.Serializer):
    queue_count = serializers.IntegerField()
    fresh_count = serializers.IntegerField()
    aging_count = serializers.IntegerField()
    overdue_count = serializers.IntegerField()
    highest_urgency_scope = serializers.CharField(required=False, allow_null=True)
    aging_summary = serializers.CharField()
    items = RuntimeTuningReviewAgingItemSerializer(many=True)


class RuntimeTuningReviewAgingDetailSerializer(RuntimeTuningReviewAgingItemSerializer):
    aging_summary = serializers.CharField()


class RuntimeTuningReviewEscalationItemSerializer(RuntimeTuningReviewAgingItemSerializer):
    escalation_level = serializers.CharField()
    escalation_rank = serializers.IntegerField()
    requires_immediate_attention = serializers.BooleanField()
    escalation_reason_codes = serializers.ListField(child=serializers.CharField())


class RuntimeTuningReviewEscalationSerializer(serializers.Serializer):
    queue_count = serializers.IntegerField()
    escalated_count = serializers.IntegerField()
    urgent_count = serializers.IntegerField()
    elevated_count = serializers.IntegerField()
    monitor_count = serializers.IntegerField()
    highest_escalation_scope = serializers.CharField(required=False, allow_null=True)
    escalation_summary = serializers.CharField()
    items = RuntimeTuningReviewEscalationItemSerializer(many=True)


class RuntimeTuningReviewEscalationDetailSerializer(RuntimeTuningReviewEscalationItemSerializer):
    escalation_summary = serializers.CharField()


class RuntimeTuningAutotriageTopScopeSerializer(serializers.Serializer):
    source_scope = serializers.CharField()
    effective_review_status = serializers.CharField()
    attention_priority = serializers.CharField()
    age_bucket = serializers.CharField()
    escalation_level = serializers.CharField()
    requires_immediate_attention = serializers.BooleanField()
    review_summary = serializers.CharField()
    technical_summary = serializers.CharField()
    runtime_investigation_deep_link = serializers.CharField()
    age_days = serializers.IntegerField(required=False, allow_null=True)
    last_action_at = serializers.DateTimeField(required=False, allow_null=True)


class RuntimeTuningAutotriageSerializer(serializers.Serializer):
    generated_at = serializers.DateTimeField()
    human_attention_mode = serializers.CharField()
    requires_human_now = serializers.BooleanField()
    can_defer_human_review = serializers.BooleanField()
    unresolved_count = serializers.IntegerField()
    urgent_count = serializers.IntegerField()
    overdue_count = serializers.IntegerField()
    recent_activity_count = serializers.IntegerField()
    next_recommended_scope = serializers.CharField(required=False, allow_null=True)
    next_recommended_reason_codes = serializers.ListField(child=serializers.CharField())
    autotriage_summary = serializers.CharField()
    top_scopes = RuntimeTuningAutotriageTopScopeSerializer(many=True)


class RuntimeTuningAutotriageDetailSerializer(RuntimeTuningAutotriageTopScopeSerializer):
    generated_at = serializers.DateTimeField()
    human_attention_mode = serializers.CharField()
    next_recommended_scope = serializers.CharField(required=False, allow_null=True)
    next_recommended_reason_codes = serializers.ListField(child=serializers.CharField())


class RuntimeTuningAutotriageAlertSyncSerializer(serializers.Serializer):
    human_attention_mode = serializers.CharField()
    alert_needed = serializers.BooleanField()
    alert_action = serializers.ChoiceField(choices=['CREATED', 'UPDATED', 'RESOLVED', 'NOOP'])
    alert_severity = serializers.CharField(required=False, allow_null=True)
    next_recommended_scope = serializers.CharField(required=False, allow_null=True)
    autotriage_summary = serializers.CharField()
    alert_status_summary = serializers.CharField()


class RuntimeTuningAutotriageAlertStatusSerializer(serializers.Serializer):
    human_attention_mode = serializers.CharField()
    alert_needed = serializers.BooleanField()
    active_alert_present = serializers.BooleanField()
    active_alert_severity = serializers.CharField(required=False, allow_null=True)
    next_recommended_scope = serializers.CharField(required=False, allow_null=True)
    autotriage_summary = serializers.CharField()
    status_summary = serializers.CharField()


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


class RuntimeTuningReviewStateSerializer(serializers.Serializer):
    source_scope = serializers.CharField()
    effective_review_status = serializers.CharField()
    stored_review_status = serializers.CharField()
    latest_snapshot_id = serializers.IntegerField()
    last_reviewed_snapshot_id = serializers.IntegerField(allow_null=True)
    has_newer_snapshot_than_reviewed = serializers.BooleanField()
    last_action_type = serializers.CharField(allow_blank=True)
    last_action_at = serializers.DateTimeField(required=False, allow_null=True)
    review_summary = serializers.CharField()
    runtime_deep_link = serializers.CharField()
    runtime_investigation_deep_link = serializers.CharField()


class RuntimeTuningReviewActionSerializer(serializers.ModelSerializer):
    snapshot_id = serializers.IntegerField(source='snapshot_id_value', allow_null=True)

    class Meta:
        model = RuntimeTuningReviewAction
        fields = [
            'id',
            'source_scope',
            'action_type',
            'snapshot_id',
            'resulting_review_status',
            'created_at',
        ]


class RuntimeTuningReviewActivityItemSerializer(serializers.Serializer):
    source_scope = serializers.CharField()
    action_type = serializers.CharField()
    created_at = serializers.DateTimeField()
    resulting_review_status = serializers.CharField()
    snapshot_id = serializers.IntegerField(allow_null=True)
    activity_label = serializers.CharField()
    activity_reason_codes = serializers.ListField(child=serializers.CharField())
    scope_review_summary = serializers.CharField()
    runtime_investigation_deep_link = serializers.CharField()
    effective_review_status = serializers.CharField(required=False)
    has_newer_snapshot_than_reviewed = serializers.BooleanField(required=False)


class RuntimeTuningReviewActivitySerializer(serializers.Serializer):
    activity_count = serializers.IntegerField()
    latest_action_at = serializers.DateTimeField(required=False, allow_null=True)
    activity_summary = serializers.CharField()
    items = RuntimeTuningReviewActivityItemSerializer(many=True)


class RuntimeTuningReviewActivityDetailSerializer(serializers.Serializer):
    source_scope = serializers.CharField()
    activity_count = serializers.IntegerField()
    latest_action_at = serializers.DateTimeField()
    scope_activity_summary = serializers.CharField()
    items = RuntimeTuningReviewActivityItemSerializer(many=True)

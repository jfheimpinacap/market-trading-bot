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
    AutonomousScheduleProfile,
    AutonomousSessionAnomaly,
    AutonomousProfileRecommendation,
    AutonomousProfileSelectionRun,
    AutonomousProfileSwitchDecision,
    AutonomousProfileSwitchRecord,
    AutonomousSessionHealthRecommendation,
    AutonomousSessionHealthRun,
    AutonomousSessionHealthSnapshot,
    AutonomousSessionInterventionDecision,
    AutonomousSessionInterventionRecord,
    AutonomousSessionRecoveryRecommendation,
    AutonomousSessionRecoveryRun,
    AutonomousSessionRecoverySnapshot,
    AutonomousRecoveryBlocker,
    AutonomousResumeApplyMode,
    AutonomousResumeDecision,
    AutonomousResumeRecord,
    AutonomousSessionContextReview,
    AutonomousSessionTimingSnapshot,
    AutonomousStopConditionEvaluation,
    AutonomousSessionRecommendation,
    AutonomousTimingDecision,
    AutonomousTimingRecommendation,
    AutonomousTickDispatchAttempt,
    AutonomousSessionAdmissionDecision,
    AutonomousSessionAdmissionRecommendation,
    AutonomousSessionAdmissionRun,
    AutonomousGlobalCapacitySnapshot,
    AutonomousSessionAdmissionReview,
    GovernanceReviewItem,
    GovernanceReviewQueueRun,
    GovernanceAutoResolutionRun,
    GovernanceAutoResolutionDecision,
    GovernanceAutoResolutionRecord,
    GovernanceReviewResolution,
    GovernanceReviewResolutionType,
    GovernanceReviewRecommendation,
    GovernanceQueueAgingRun,
    GovernanceQueueAgingReview,
    GovernanceQueueAgingRecommendation,
    GovernanceBacklogPressureRun,
    GovernanceBacklogPressureSnapshot,
    GovernanceBacklogPressureDecision,
    GovernanceBacklogPressureRecommendation,
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


class LivePaperBootstrapRequestSerializer(serializers.Serializer):
    preset = serializers.CharField(required=False, allow_blank=True, default='live_read_only_paper_conservative')
    auto_start_heartbeat = serializers.BooleanField(required=False, default=True)
    start_now = serializers.BooleanField(required=False, default=True)


class ExtendedPaperRunLaunchRequestSerializer(serializers.Serializer):
    preset = serializers.CharField(required=False, allow_blank=True, default='live_read_only_paper_conservative')


class ExtendedPaperRunLaunchSerializer(serializers.Serializer):
    preset_name = serializers.CharField()
    launch_status = serializers.ChoiceField(
        choices=['STARTED', 'REUSED_RUNNING_SESSION', 'REUSED_PAUSED_SESSION', 'BLOCKED', 'FAILED']
    )
    gate_status = serializers.ChoiceField(choices=['ALLOW', 'ALLOW_WITH_CAUTION', 'BLOCK'])
    session_active = serializers.BooleanField()
    heartbeat_active = serializers.BooleanField()
    current_session_status = serializers.CharField()
    caution_mode = serializers.BooleanField(required=False, allow_null=True)
    next_action_hint = serializers.CharField()
    launch_summary = serializers.CharField()
    reason_codes = serializers.ListField(child=serializers.CharField())


class ExtendedPaperRunStatusSerializer(serializers.Serializer):
    preset_name = serializers.CharField()
    extended_run_active = serializers.BooleanField()
    gate_status = serializers.ChoiceField(choices=['ALLOW', 'ALLOW_WITH_CAUTION', 'BLOCK'])
    session_active = serializers.BooleanField()
    heartbeat_active = serializers.BooleanField()
    current_session_status = serializers.CharField()
    caution_mode = serializers.BooleanField(required=False, allow_null=True)
    status_summary = serializers.CharField()
    next_action_hint = serializers.CharField()


class LivePaperAttentionAlertSyncSerializer(serializers.Serializer):
    attention_needed = serializers.BooleanField()
    attention_mode = serializers.ChoiceField(choices=['HEALTHY', 'DEGRADED', 'REVIEW_NOW', 'BLOCKED'])
    alert_action = serializers.ChoiceField(choices=['CREATED', 'UPDATED', 'RESOLVED', 'NOOP'])
    alert_severity = serializers.ChoiceField(choices=['warning', 'high', 'critical'], allow_null=True, required=False)
    session_active = serializers.BooleanField()
    heartbeat_active = serializers.BooleanField()
    current_session_status = serializers.CharField()
    attention_reason_codes = serializers.ListField(child=serializers.CharField(), required=False)
    status_summary = serializers.CharField()
    alert_status_summary = serializers.CharField()
    material_change_detected = serializers.BooleanField(required=False)
    material_change_fields = serializers.ListField(child=serializers.CharField(), required=False)
    update_suppressed = serializers.BooleanField(required=False)
    suppression_reason = serializers.CharField(required=False, allow_null=True)
    active_alert_present = serializers.BooleanField(required=False)
    funnel_status = serializers.ChoiceField(choices=['ACTIVE', 'THIN_FLOW', 'STALLED'], required=False, allow_null=True)
    stalled_stage = serializers.CharField(required=False, allow_null=True)
    top_stage = serializers.CharField(required=False, allow_null=True)
    funnel_summary = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class LivePaperAttentionAlertStatusSerializer(serializers.Serializer):
    attention_needed = serializers.BooleanField()
    attention_mode = serializers.ChoiceField(choices=['HEALTHY', 'DEGRADED', 'REVIEW_NOW', 'BLOCKED'])
    active_alert_present = serializers.BooleanField()
    active_alert_severity = serializers.ChoiceField(choices=['warning', 'high', 'critical'], allow_null=True, required=False)
    session_active = serializers.BooleanField()
    heartbeat_active = serializers.BooleanField()
    current_session_status = serializers.CharField()
    status_summary = serializers.CharField()
    funnel_status = serializers.ChoiceField(choices=['ACTIVE', 'THIN_FLOW', 'STALLED'], required=False, allow_null=True)
    stalled_stage = serializers.CharField(required=False, allow_null=True)
    top_stage = serializers.CharField(required=False, allow_null=True)
    funnel_summary = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    last_alert_action = serializers.CharField(required=False, allow_null=True)
    last_sync_summary = serializers.CharField(required=False, allow_null=True)
    last_auto_sync = serializers.DictField(required=False)




class LivePaperSmokeTestRequestSerializer(serializers.Serializer):
    preset = serializers.CharField(required=False, allow_blank=True, default='live_read_only_paper_conservative')
    heartbeat_passes = serializers.IntegerField(required=False, min_value=1, max_value=2, default=1)


class LivePaperSmokeTestCheckSerializer(serializers.Serializer):
    check_name = serializers.CharField()
    status = serializers.ChoiceField(choices=['PASS', 'WARN', 'FAIL'])
    summary = serializers.CharField()


class LivePaperSmokeTestResultSerializer(serializers.Serializer):
    preset_name = serializers.CharField()
    smoke_test_status = serializers.ChoiceField(choices=['PASS', 'WARN', 'FAIL'])
    executed_at = serializers.DateTimeField()
    bootstrap_action = serializers.CharField()
    session_active_after = serializers.BooleanField()
    heartbeat_active_after = serializers.BooleanField()
    validation_status_before = serializers.ChoiceField(choices=['READY', 'WARNING', 'BLOCKED'])
    validation_status_after = serializers.ChoiceField(choices=['READY', 'WARNING', 'BLOCKED'])
    heartbeat_passes_requested = serializers.IntegerField()
    heartbeat_passes_completed = serializers.IntegerField()
    recent_activity_detected = serializers.BooleanField()
    recent_trades_detected = serializers.BooleanField()
    next_action_hint = serializers.CharField()
    smoke_test_summary = serializers.CharField()
    checks = LivePaperSmokeTestCheckSerializer(many=True)


class LivePaperSmokeTestStatusSerializer(serializers.Serializer):
    preset_name = serializers.CharField()
    smoke_test_status = serializers.ChoiceField(choices=['PASS', 'WARN', 'FAIL'])
    executed_at = serializers.DateTimeField()
    validation_status_after = serializers.ChoiceField(choices=['READY', 'WARNING', 'BLOCKED'])
    heartbeat_passes_completed = serializers.IntegerField()
    smoke_test_summary = serializers.CharField()
    next_action_hint = serializers.CharField()

class LivePaperValidationCheckSerializer(serializers.Serializer):
    check_name = serializers.CharField()
    status = serializers.ChoiceField(choices=['PASS', 'WARN', 'FAIL'])
    summary = serializers.CharField()


class LivePaperValidationDigestSerializer(serializers.Serializer):
    preset_name = serializers.CharField()
    validation_status = serializers.ChoiceField(choices=['READY', 'WARNING', 'BLOCKED'])
    session_active = serializers.BooleanField()
    heartbeat_active = serializers.BooleanField()
    attention_mode = serializers.ChoiceField(choices=['HEALTHY', 'DEGRADED', 'REVIEW_NOW', 'BLOCKED'])
    paper_account_ready = serializers.BooleanField()
    market_data_ready = serializers.BooleanField()
    portfolio_snapshot_ready = serializers.BooleanField()
    recent_activity_present = serializers.BooleanField()
    recent_trades_present = serializers.BooleanField()
    cash_available = serializers.FloatField(allow_null=True)
    equity_available = serializers.FloatField(allow_null=True)
    next_action_hint = serializers.CharField()
    validation_summary = serializers.CharField()
    checks = LivePaperValidationCheckSerializer(many=True)


class LivePaperTrialRunRequestSerializer(serializers.Serializer):
    preset = serializers.CharField(required=False, allow_blank=True, default='live_read_only_paper_conservative')
    heartbeat_passes = serializers.IntegerField(required=False, min_value=1, max_value=2, default=1)


class LivePaperTrialRunCheckSerializer(serializers.Serializer):
    check_name = serializers.CharField()
    status = serializers.ChoiceField(choices=['PASS', 'WARN', 'FAIL'])
    summary = serializers.CharField()


class LivePaperTrialRunResultSerializer(serializers.Serializer):
    preset_name = serializers.CharField()
    trial_status = serializers.ChoiceField(choices=['PASS', 'WARN', 'FAIL'])
    executed_at = serializers.DateTimeField()
    bootstrap_action = serializers.CharField()
    smoke_test_status = serializers.ChoiceField(choices=['PASS', 'WARN', 'FAIL'])
    validation_status_before = serializers.ChoiceField(choices=['READY', 'WARNING', 'BLOCKED'])
    validation_status_after = serializers.ChoiceField(choices=['READY', 'WARNING', 'BLOCKED'])
    heartbeat_passes_requested = serializers.IntegerField()
    heartbeat_passes_completed = serializers.IntegerField()
    recent_activity_detected = serializers.BooleanField()
    recent_trades_detected = serializers.BooleanField()
    portfolio_snapshot_ready = serializers.BooleanField()
    next_action_hint = serializers.CharField()
    trial_summary = serializers.CharField()
    checks = LivePaperTrialRunCheckSerializer(many=True)


class LivePaperTrialRunStatusSerializer(serializers.Serializer):
    preset_name = serializers.CharField()
    trial_status = serializers.ChoiceField(choices=['PASS', 'WARN', 'FAIL'])
    executed_at = serializers.DateTimeField()
    smoke_test_status = serializers.ChoiceField(choices=['PASS', 'WARN', 'FAIL'])
    validation_status_after = serializers.ChoiceField(choices=['READY', 'WARNING', 'BLOCKED'])
    heartbeat_passes_completed = serializers.IntegerField()
    trial_summary = serializers.CharField()
    next_action_hint = serializers.CharField()


class LivePaperTrialRunHistoryQuerySerializer(serializers.Serializer):
    limit = serializers.IntegerField(required=False, min_value=1, max_value=20, default=5)
    status = serializers.ChoiceField(choices=['PASS', 'WARN', 'FAIL'], required=False)


class LivePaperTrialRunHistoryItemSerializer(serializers.Serializer):
    created_at = serializers.DateTimeField()
    preset_name = serializers.CharField()
    trial_status = serializers.ChoiceField(choices=['PASS', 'WARN', 'FAIL'])
    bootstrap_action = serializers.CharField()
    smoke_test_status = serializers.ChoiceField(choices=['PASS', 'WARN', 'FAIL'])
    validation_status_after = serializers.ChoiceField(choices=['READY', 'WARNING', 'BLOCKED'])
    heartbeat_passes_completed = serializers.IntegerField()
    next_action_hint = serializers.CharField()
    trial_summary = serializers.CharField()
    recent_activity_detected = serializers.BooleanField(required=False)
    recent_trades_detected = serializers.BooleanField(required=False)
    portfolio_snapshot_ready = serializers.BooleanField(required=False)


class LivePaperTrialRunHistorySerializer(serializers.Serializer):
    count = serializers.IntegerField()
    latest_trial_status = serializers.ChoiceField(choices=['PASS', 'WARN', 'FAIL'], required=False, allow_null=True)
    history_summary = serializers.CharField()
    items = LivePaperTrialRunHistoryItemSerializer(many=True)


class LivePaperTrialTrendQuerySerializer(serializers.Serializer):
    limit = serializers.IntegerField(required=False, min_value=1, max_value=20, default=5)
    preset = serializers.CharField(required=False, allow_blank=False)


class LivePaperTrialTrendCountsSerializer(serializers.Serializer):
    pass_count = serializers.IntegerField(min_value=0)
    warn_count = serializers.IntegerField(min_value=0)
    fail_count = serializers.IntegerField(min_value=0)


class LivePaperTrialTrendDigestSerializer(serializers.Serializer):
    sample_size = serializers.IntegerField(min_value=0)
    latest_trial_status = serializers.ChoiceField(choices=['PASS', 'WARN', 'FAIL'], required=False, allow_null=True)
    latest_validation_status = serializers.ChoiceField(choices=['READY', 'WARNING', 'BLOCKED'], required=False, allow_null=True)
    trend_status = serializers.ChoiceField(choices=['IMPROVING', 'STABLE', 'DEGRADING', 'INSUFFICIENT_DATA'])
    readiness_status = serializers.ChoiceField(choices=['READY_FOR_EXTENDED_RUN', 'NEEDS_REVIEW', 'NOT_READY'])
    trend_summary = serializers.CharField()
    next_action_hint = serializers.CharField()
    counts = LivePaperTrialTrendCountsSerializer()
    recent_statuses = serializers.ListField(
        child=serializers.ChoiceField(choices=['PASS', 'WARN', 'FAIL']),
        required=False,
    )


class LivePaperAutonomyFunnelStageSerializer(serializers.Serializer):
    stage_name = serializers.ChoiceField(choices=['scan', 'research', 'prediction', 'risk', 'paper_execution'])
    count = serializers.IntegerField(min_value=0)
    status = serializers.ChoiceField(choices=['ACTIVE', 'LOW', 'EMPTY'])
    summary = serializers.CharField()


class LivePaperAutonomyFunnelSerializer(serializers.Serializer):
    window_minutes = serializers.IntegerField(min_value=5, max_value=1440)
    preset_name = serializers.CharField()
    funnel_status = serializers.ChoiceField(choices=['ACTIVE', 'THIN_FLOW', 'STALLED'])
    scan_count = serializers.IntegerField(min_value=0)
    research_count = serializers.IntegerField(min_value=0)
    prediction_count = serializers.IntegerField(min_value=0)
    risk_approved_count = serializers.IntegerField(min_value=0)
    risk_blocked_count = serializers.IntegerField(min_value=0)
    risk_decision_count = serializers.IntegerField(min_value=0)
    paper_execution_count = serializers.IntegerField(min_value=0)
    recent_trades_count = serializers.IntegerField(min_value=0)
    top_stage = serializers.ChoiceField(choices=['scan', 'research', 'prediction', 'risk', 'paper_execution'])
    stalled_stage = serializers.ChoiceField(choices=['scan', 'research', 'prediction', 'risk', 'paper_execution'], allow_null=True)
    stalled_reason_code = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    stalled_missing_counter = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    handoff_reason_codes = serializers.ListField(child=serializers.CharField(), required=False)
    stage_source_mismatch = serializers.DictField(required=False)
    handoff_summary = serializers.CharField(required=False, allow_blank=True)
    paper_execution_summary = serializers.CharField(required=False, allow_blank=True)
    paper_execution_route_expected = serializers.IntegerField(min_value=0, required=False)
    paper_execution_route_available = serializers.IntegerField(min_value=0, required=False)
    paper_execution_route_attempted = serializers.IntegerField(min_value=0, required=False)
    paper_execution_route_created = serializers.IntegerField(min_value=0, required=False)
    paper_execution_route_reused = serializers.IntegerField(min_value=0, required=False)
    paper_execution_route_blocked = serializers.IntegerField(min_value=0, required=False)
    paper_execution_route_missing_status_count = serializers.IntegerField(min_value=0, required=False)
    paper_execution_route_reason_codes = serializers.ListField(child=serializers.CharField(), required=False)
    paper_execution_examples = serializers.ListField(child=serializers.DictField(), required=False)
    paper_execution_created_count = serializers.IntegerField(min_value=0, required=False)
    paper_execution_reused_count = serializers.IntegerField(min_value=0, required=False)
    paper_execution_visible_count = serializers.IntegerField(min_value=0, required=False)
    paper_execution_hidden_count = serializers.IntegerField(min_value=0, required=False)
    paper_execution_visibility_reason_codes = serializers.ListField(child=serializers.CharField(), required=False)
    paper_execution_visibility_summary = serializers.CharField(required=False, allow_blank=True)
    paper_execution_visibility_examples = serializers.ListField(child=serializers.DictField(), required=False)
    paper_trade_summary = serializers.CharField(required=False, allow_blank=True)
    paper_trade_route_expected = serializers.IntegerField(min_value=0, required=False)
    paper_trade_route_available = serializers.IntegerField(min_value=0, required=False)
    paper_trade_route_attempted = serializers.IntegerField(min_value=0, required=False)
    paper_trade_route_created = serializers.IntegerField(min_value=0, required=False)
    paper_trade_route_reused = serializers.IntegerField(min_value=0, required=False)
    paper_trade_route_blocked = serializers.IntegerField(min_value=0, required=False)
    paper_trade_route_reason_codes = serializers.ListField(child=serializers.CharField(), required=False)
    paper_trade_decision_created = serializers.IntegerField(min_value=0, required=False)
    paper_trade_decision_reused = serializers.IntegerField(min_value=0, required=False)
    paper_trade_decision_blocked = serializers.IntegerField(min_value=0, required=False)
    paper_trade_decision_dedupe_applied = serializers.IntegerField(min_value=0, required=False)
    paper_trade_decision_reason_codes = serializers.ListField(child=serializers.CharField(), required=False)
    paper_trade_decision_summary = serializers.CharField(required=False, allow_blank=True)
    paper_trade_decision_examples = serializers.ListField(child=serializers.DictField(), required=False)
    paper_trade_final_summary = serializers.CharField(required=False, allow_blank=True)
    final_trade_expected = serializers.IntegerField(min_value=0, required=False)
    final_trade_available = serializers.IntegerField(min_value=0, required=False)
    final_trade_attempted = serializers.IntegerField(min_value=0, required=False)
    final_trade_created = serializers.IntegerField(min_value=0, required=False)
    final_trade_reused = serializers.IntegerField(min_value=0, required=False)
    final_trade_blocked = serializers.IntegerField(min_value=0, required=False)
    final_trade_reason_codes = serializers.ListField(child=serializers.CharField(), required=False)
    paper_trade_final_examples = serializers.ListField(child=serializers.DictField(), required=False)
    paper_trade_examples = serializers.ListField(child=serializers.DictField(), required=False)
    execution_candidate_creation_gate_summary = serializers.DictField(required=False)
    execution_candidate_creation_gate_examples = serializers.ListField(child=serializers.DictField(), required=False)
    execution_exposure_provenance_summary = serializers.DictField(required=False)
    execution_exposure_provenance_examples = serializers.ListField(child=serializers.DictField(), required=False)
    execution_exposure_release_audit_summary = serializers.DictField(required=False)
    execution_exposure_release_audit_examples = serializers.ListField(child=serializers.DictField(), required=False)
    active_exposure_readiness_throttle_summary = serializers.DictField(required=False)
    active_exposure_readiness_throttle_examples = serializers.ListField(child=serializers.DictField(), required=False)
    execution_promotion_gate_summary = serializers.DictField(required=False)
    execution_promotion_gate_examples = serializers.ListField(child=serializers.DictField(), required=False)
    execution_lineage_summary = serializers.DictField(required=False)
    final_fanout_summary = serializers.DictField(required=False)
    cash_pressure_summary = serializers.DictField(required=False)
    position_exposure_summary = serializers.DictField(required=False)
    prediction_intake_summary = serializers.DictField(required=False)
    prediction_intake_examples = serializers.ListField(child=serializers.DictField(), required=False)
    shortlisted_signals = serializers.IntegerField(min_value=0, required=False)
    handoff_candidates = serializers.IntegerField(min_value=0, required=False)
    consensus_reviews = serializers.IntegerField(min_value=0, required=False)
    prediction_candidates = serializers.IntegerField(min_value=0, required=False)
    risk_decisions = serializers.IntegerField(min_value=0, required=False)
    paper_execution_candidates = serializers.IntegerField(min_value=0, required=False)
    next_action_hint = serializers.CharField()
    funnel_summary = serializers.CharField()
    stages = LivePaperAutonomyFunnelStageSerializer(many=True)


class ExtendedPaperRunGateCheckSerializer(serializers.Serializer):
    check_name = serializers.ChoiceField(
        choices=['validation', 'trial_trend', 'operational_attention', 'autonomy_funnel', 'recent_trial_quality']
    )
    status = serializers.ChoiceField(choices=['PASS', 'WARN', 'FAIL'])
    summary = serializers.CharField()


class ExtendedPaperRunGateSerializer(serializers.Serializer):
    preset_name = serializers.CharField()
    gate_status = serializers.ChoiceField(choices=['ALLOW', 'ALLOW_WITH_CAUTION', 'BLOCK'])
    latest_trial_status = serializers.ChoiceField(choices=['PASS', 'WARN', 'FAIL'], allow_null=True, required=False)
    trend_status = serializers.ChoiceField(choices=['IMPROVING', 'STABLE', 'DEGRADING', 'INSUFFICIENT_DATA'])
    readiness_status = serializers.ChoiceField(choices=['READY_FOR_EXTENDED_RUN', 'NEEDS_REVIEW', 'NOT_READY'])
    validation_status = serializers.ChoiceField(choices=['READY', 'WARNING', 'BLOCKED'])
    attention_mode = serializers.ChoiceField(choices=['HEALTHY', 'DEGRADED', 'REVIEW_NOW', 'BLOCKED'])
    funnel_status = serializers.ChoiceField(choices=['ACTIVE', 'THIN_FLOW', 'STALLED'])
    next_action_hint = serializers.CharField()
    gate_summary = serializers.CharField()
    reason_codes = serializers.ListField(child=serializers.CharField())
    checks = ExtendedPaperRunGateCheckSerializer(many=True)
    state_mismatch_summary = serializers.DictField(required=False)
    state_mismatch_examples = serializers.ListField(child=serializers.DictField(), required=False)
    gate_source_summary = serializers.DictField(required=False)




class TestConsoleStartRequestSerializer(serializers.Serializer):
    preset = serializers.CharField(required=False, allow_blank=True, default='live_read_only_paper_conservative')


class TestConsoleStopRequestSerializer(serializers.Serializer):
    preset = serializers.CharField(required=False, allow_blank=True, default='live_read_only_paper_conservative')


class TestConsoleStatusSerializer(serializers.Serializer):
    test_status = serializers.ChoiceField(choices=['IDLE', 'RUNNING', 'STOPPED', 'COMPLETED', 'COMPLETED_WITH_WARNINGS', 'BLOCKED', 'FAILED'])
    current_phase = serializers.CharField(required=False, allow_null=True)
    started_at = serializers.DateTimeField(required=False, allow_null=True)
    ended_at = serializers.DateTimeField(required=False, allow_null=True)
    preset_name = serializers.CharField()
    session_active = serializers.BooleanField()
    heartbeat_active = serializers.BooleanField()
    current_session_status = serializers.CharField()
    validation_status = serializers.CharField()
    trial_status = serializers.CharField()
    trend_status = serializers.CharField()
    readiness_status = serializers.CharField()
    gate_status = serializers.CharField()
    extended_run_status = serializers.CharField()
    funnel_status = serializers.CharField()
    funnel_status_window = serializers.CharField(required=False)
    active_operational_overlay_summary = serializers.DictField(required=False)
    handoff_summary = serializers.DictField(required=False)
    llm_shadow_summary = serializers.DictField(required=False)
    latest_llm_shadow_summary = serializers.DictField(required=False)
    llm_shadow_history_count = serializers.IntegerField(required=False)
    llm_shadow_recent_history = serializers.ListField(child=serializers.DictField(), required=False)
    llm_aux_signal_summary = serializers.DictField(required=False)
    paper_execution_summary = serializers.DictField(required=False)
    paper_execution_examples = serializers.ListField(child=serializers.DictField(), required=False)
    paper_execution_visibility_summary = serializers.DictField(required=False)
    paper_execution_visibility_examples = serializers.ListField(child=serializers.DictField(), required=False)
    paper_trade_summary = serializers.DictField(required=False)
    paper_trade_examples = serializers.ListField(child=serializers.DictField(), required=False)
    paper_trade_decision_summary = serializers.DictField(required=False)
    paper_trade_decision_examples = serializers.ListField(child=serializers.DictField(), required=False)
    paper_trade_final_summary = serializers.DictField(required=False)
    paper_trade_final_examples = serializers.ListField(child=serializers.DictField(), required=False)
    execution_candidate_creation_gate_summary = serializers.DictField(required=False)
    execution_candidate_creation_gate_examples = serializers.ListField(child=serializers.DictField(), required=False)
    execution_exposure_provenance_summary = serializers.DictField(required=False)
    execution_exposure_provenance_examples = serializers.ListField(child=serializers.DictField(), required=False)
    execution_exposure_release_audit_summary = serializers.DictField(required=False)
    execution_exposure_release_audit_examples = serializers.ListField(child=serializers.DictField(), required=False)
    execution_promotion_gate_summary = serializers.DictField(required=False)
    execution_promotion_gate_examples = serializers.ListField(child=serializers.DictField(), required=False)
    execution_lineage_summary = serializers.DictField(required=False)
    final_fanout_summary = serializers.DictField(required=False)
    final_fanout_examples = serializers.ListField(child=serializers.DictField(), required=False)
    cash_pressure_summary = serializers.DictField(required=False)
    cash_pressure_examples = serializers.ListField(child=serializers.DictField(), required=False)
    position_exposure_summary = serializers.DictField(required=False)
    prediction_intake_summary = serializers.DictField(required=False)
    prediction_intake_examples = serializers.ListField(child=serializers.DictField(), required=False)
    attention_mode = serializers.CharField()
    portfolio_summary = serializers.DictField(required=False)
    portfolio_trade_reconciliation_summary = serializers.DictField(required=False)
    scan_summary = serializers.DictField(required=False)
    state_mismatch_summary = serializers.DictField(required=False)
    state_mismatch_examples = serializers.ListField(child=serializers.DictField(), required=False)
    blocker_summary = serializers.ListField(child=serializers.CharField(), required=False)
    next_action_hint = serializers.CharField()
    warnings = serializers.ListField(child=serializers.CharField(), required=False)
    errors = serializers.ListField(child=serializers.CharField(), required=False)
    reason_codes = serializers.ListField(child=serializers.CharField(), required=False)
    summary = serializers.CharField(required=False)
    current_step = serializers.IntegerField(required=False, allow_null=True)
    current_step_label = serializers.CharField(required=False, allow_blank=True)
    completed_steps = serializers.IntegerField(required=False)
    total_steps = serializers.IntegerField(required=False)
    progress_state = serializers.CharField(required=False)
    updated_at = serializers.DateTimeField(required=False, allow_null=True)
    elapsed_seconds = serializers.IntegerField(required=False, allow_null=True)
    last_event = serializers.CharField(required=False, allow_blank=True)
    last_reason_code = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    export_available = serializers.BooleanField(required=False)
    is_stale = serializers.BooleanField(required=False)


class TestConsoleExportLogQuerySerializer(serializers.Serializer):
    format = serializers.ChoiceField(choices=['text', 'json'], required=False, default='text')


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


class AutonomousScheduleProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomousScheduleProfile
        fields = '__all__'


class AutonomousSessionTimingSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomousSessionTimingSnapshot
        fields = '__all__'


class AutonomousStopConditionEvaluationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomousStopConditionEvaluation
        fields = '__all__'


class AutonomousTimingDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomousTimingDecision
        fields = '__all__'


class AutonomousTimingRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomousTimingRecommendation
        fields = '__all__'


class SessionTimingReviewRequestSerializer(serializers.Serializer):
    session_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        allow_empty=True,
    )


class ProfileSelectionReviewRequestSerializer(serializers.Serializer):
    session_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        allow_empty=True,
    )
    apply_switches = serializers.BooleanField(required=False, default=True)


class SessionHealthReviewRequestSerializer(serializers.Serializer):
    session_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        allow_empty=True,
    )
    auto_apply_safe = serializers.BooleanField(required=False, default=True)


class SessionRecoveryReviewRequestSerializer(serializers.Serializer):
    session_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        allow_empty=True,
    )
    auto_apply_safe = serializers.BooleanField(required=False, default=False)


class ApplySessionResumeRequestSerializer(serializers.Serializer):
    applied_mode = serializers.ChoiceField(
        choices=AutonomousResumeApplyMode.choices,
        required=False,
        default=AutonomousResumeApplyMode.MANUAL_RESUME,
    )


class AutonomousProfileSelectionRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomousProfileSelectionRun
        fields = '__all__'


class AutonomousSessionContextReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomousSessionContextReview
        fields = '__all__'


class AutonomousProfileSwitchDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomousProfileSwitchDecision
        fields = '__all__'


class AutonomousProfileSwitchRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomousProfileSwitchRecord
        fields = '__all__'


class AutonomousProfileRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomousProfileRecommendation
        fields = '__all__'


class AutonomousSessionHealthRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomousSessionHealthRun
        fields = '__all__'


class AutonomousSessionHealthSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomousSessionHealthSnapshot
        fields = '__all__'


class AutonomousSessionAnomalySerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomousSessionAnomaly
        fields = '__all__'


class AutonomousSessionInterventionDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomousSessionInterventionDecision
        fields = '__all__'


class AutonomousSessionInterventionRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomousSessionInterventionRecord
        fields = '__all__'


class AutonomousSessionHealthRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomousSessionHealthRecommendation
        fields = '__all__'


class AutonomousSessionRecoveryRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomousSessionRecoveryRun
        fields = '__all__'


class AutonomousSessionRecoverySnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomousSessionRecoverySnapshot
        fields = '__all__'


class AutonomousRecoveryBlockerSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomousRecoveryBlocker
        fields = '__all__'


class AutonomousResumeDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomousResumeDecision
        fields = '__all__'


class AutonomousResumeRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomousResumeRecord
        fields = '__all__'


class AutonomousSessionRecoveryRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomousSessionRecoveryRecommendation
        fields = '__all__'


class SessionAdmissionReviewRequestSerializer(serializers.Serializer):
    session_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        allow_empty=True,
    )
    auto_apply_safe = serializers.BooleanField(required=False, default=True)


class AutonomousSessionAdmissionRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomousSessionAdmissionRun
        fields = '__all__'


class AutonomousGlobalCapacitySnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomousGlobalCapacitySnapshot
        fields = '__all__'


class AutonomousSessionAdmissionReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomousSessionAdmissionReview
        fields = '__all__'


class AutonomousSessionAdmissionDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomousSessionAdmissionDecision
        fields = '__all__'


class AutonomousSessionAdmissionRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomousSessionAdmissionRecommendation
        fields = '__all__'


class GovernanceReviewQueueRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = GovernanceReviewQueueRun
        fields = '__all__'


class GovernanceReviewItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = GovernanceReviewItem
        fields = '__all__'


class GovernanceReviewRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = GovernanceReviewRecommendation
        fields = '__all__'


class GovernanceReviewResolutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = GovernanceReviewResolution
        fields = '__all__'


class ResolveGovernanceReviewItemRequestSerializer(serializers.Serializer):
    resolution_type = serializers.ChoiceField(choices=GovernanceReviewResolutionType.choices)
    resolution_summary = serializers.CharField(required=False, allow_blank=True)
    metadata = serializers.JSONField(required=False)


class GovernanceAutoResolutionRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = GovernanceAutoResolutionRun
        fields = '__all__'


class GovernanceAutoResolutionDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = GovernanceAutoResolutionDecision
        fields = '__all__'


class GovernanceAutoResolutionRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = GovernanceAutoResolutionRecord
        fields = '__all__'


class GovernanceQueueAgingRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = GovernanceQueueAgingRun
        fields = '__all__'


class GovernanceQueueAgingReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = GovernanceQueueAgingReview
        fields = '__all__'


class GovernanceQueueAgingRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = GovernanceQueueAgingRecommendation
        fields = '__all__'


class GovernanceBacklogPressureRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = GovernanceBacklogPressureRun
        fields = '__all__'


class GovernanceBacklogPressureSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = GovernanceBacklogPressureSnapshot
        fields = '__all__'


class GovernanceBacklogPressureDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = GovernanceBacklogPressureDecision
        fields = '__all__'


class GovernanceBacklogPressureRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = GovernanceBacklogPressureRecommendation
        fields = '__all__'

export type RuntimeMode = 'OBSERVE_ONLY' | 'PAPER_ASSIST' | 'PAPER_SEMI_AUTO' | 'PAPER_AUTO';
export type RuntimeStatus = 'ACTIVE' | 'DEGRADED' | 'PAUSED' | 'STOPPED';

export type RuntimeState = {
  id: number;
  current_mode: RuntimeMode;
  desired_mode: RuntimeMode | null;
  status: RuntimeStatus;
  set_by: string;
  rationale: string;
  effective_at: string;
  updated_at: string;
  metadata: Record<string, unknown>;
};

export type RuntimeStatusResponse = {
  state: RuntimeState;
  readiness_status: 'READY' | 'CAUTION' | 'NOT_READY' | null;
  safety_status: {
    status: string;
    status_message: string;
    kill_switch_enabled: boolean;
    hard_stop_active: boolean;
  };
  constraints: {
    allowed: boolean;
    reasons: string[];
  };
  global_operating_mode: GlobalOperatingMode;
  global_mode_influence: Record<string, string>;
  global_mode_enforcement: Record<string, unknown>;
  global_mode_enforcement_run_id: number | null;
};

export type RuntimeModeOption = {
  mode: RuntimeMode;
  label: string;
  description: string;
  is_allowed_now: boolean;
  blocked_reasons: string[];
  readiness_status: string | null;
  safety_status: string;
};

export type RuntimeTransition = {
  id: number;
  from_mode: RuntimeMode | null;
  to_mode: RuntimeMode;
  from_status: RuntimeStatus | null;
  to_status: RuntimeStatus;
  trigger_source: string;
  reason: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type RuntimeCapabilities = {
  mode: RuntimeMode;
  allow_signal_generation: boolean;
  allow_proposals: boolean;
  allow_allocation: boolean;
  allow_real_market_ops: boolean;
  allow_auto_execution: boolean;
  allow_continuous_loop: boolean;
  require_operator_for_all_trades: boolean;
  allow_pending_approvals: boolean;
  allow_replay: boolean;
  allow_experiments: boolean;
  max_auto_trades_per_cycle: number;
  max_auto_trades_per_session: number;
  blocked_reasons: string[];
};

export type SetRuntimeModePayload = {
  mode: RuntimeMode;
  rationale?: string;
  set_by?: string;
  metadata?: Record<string, unknown>;
};

export type GlobalOperatingMode = 'BALANCED' | 'CAUTION' | 'MONITOR_ONLY' | 'RECOVERY_MODE' | 'THROTTLED' | 'BLOCKED';
export type RuntimeSummaryTuningContext = {
  tuning_profile_name: string;
  tuning_profile_summary?: string;
  tuning_profile_fingerprint?: string;
  tuning_effective_values: Record<string, string | number | boolean>;
  tuning_guardrail_summary: Record<string, string | number | boolean>;
};

export type RuntimeTuningDriftStatus = 'INITIAL' | 'NO_CHANGE' | 'MINOR_CONTEXT_CHANGE' | 'PROFILE_CHANGE';

export type RuntimeTuningContextSnapshot = {
  id: number;
  source_scope: 'runtime_feedback' | 'operating_mode' | 'mode_stabilization' | 'mode_enforcement';
  source_run_id: number | null;
  tuning_profile_name: string;
  tuning_profile_fingerprint: string;
  tuning_profile_summary: string;
  effective_values: Record<string, string | number | boolean>;
  drift_status: RuntimeTuningDriftStatus;
  drift_summary: string;
  created_at_snapshot: string;
  created_at: string;
  updated_at: string;
};

export type RuntimeTuningContextDriftSummary = {
  total_snapshots: number;
  status_counts: Record<RuntimeTuningDriftStatus, number>;
  latest_by_scope: Record<
    RuntimeTuningContextSnapshot['source_scope'],
    {
      latest_snapshot_id: number | null;
      source_run_id: number | null;
      tuning_profile_name: string | null;
      tuning_profile_fingerprint: string | null;
      drift_status: RuntimeTuningDriftStatus | null;
      drift_summary: string | null;
      created_at: string | null;
    }
  >;
};

export type RuntimeTuningContextDiff = {
  source_scope: RuntimeTuningContextSnapshot['source_scope'];
  current_snapshot_id: number;
  previous_snapshot_id: number | null;
  drift_status: RuntimeTuningDriftStatus;
  changed_fields: Record<string, { previous: unknown; current: unknown }>;
  unchanged_fields?: Record<string, unknown>;
  diff_summary: string;
  created_at?: string | null;
};

export type RuntimeTuningRunCorrelation = {
  source_scope: RuntimeTuningContextSnapshot['source_scope'];
  source_run_id: number | null;
  tuning_snapshot_id: number;
  tuning_profile_name: string;
  tuning_profile_fingerprint: string;
  drift_status: RuntimeTuningDriftStatus;
  run_created_at?: string | null;
  correlation_summary: string;
};

export type RuntimeTuningHistoryQuery = {
  source_scope?: RuntimeTuningContextSnapshot['source_scope'];
  drift_status?: RuntimeTuningDriftStatus;
  latest_only?: boolean;
  limit?: number;
  created_after?: string;
  created_before?: string;
};

export type RuntimeTuningRunCorrelationQuery = Pick<RuntimeTuningHistoryQuery, 'source_scope' | 'latest_only' | 'limit'>;

export type RuntimeTuningScopeDigest = {
  source_scope: RuntimeTuningContextSnapshot['source_scope'];
  latest_snapshot_id: number;
  latest_run_id: number | null;
  tuning_profile_name: string;
  tuning_profile_fingerprint: string;
  latest_drift_status: RuntimeTuningDriftStatus;
  latest_snapshot_created_at: string;
  digest_summary: string;
  latest_diff_snapshot_id: number | null;
  latest_diff_status: RuntimeTuningDriftStatus | null;
  latest_diff_summary: string | null;
};

export type RuntimeTuningAlertStatus = 'STABLE' | 'MINOR_CHANGE' | 'PROFILE_SHIFT' | 'REVIEW_NOW';

export type RuntimeTuningChangeAlert = {
  source_scope: RuntimeTuningContextSnapshot['source_scope'];
  latest_snapshot_id: number;
  tuning_profile_name: string;
  tuning_profile_fingerprint: string;
  latest_drift_status: RuntimeTuningDriftStatus;
  latest_diff_snapshot_id: number | null;
  latest_diff_status: RuntimeTuningDriftStatus | null;
  latest_diff_summary: string | null;
  alert_status: RuntimeTuningAlertStatus;
  alert_summary: string;
  created_at?: string | null;
};

export type RuntimeTuningAlertSummaryScope = {
  source_scope: RuntimeTuningContextSnapshot['source_scope'];
  alert_status: RuntimeTuningAlertStatus;
  latest_snapshot_id: number;
  created_at?: string | null;
  alert_summary: string;
};

export type RuntimeTuningAlertSummary = {
  total_scope_count: number;
  stable_count: number;
  minor_change_count: number;
  profile_shift_count: number;
  review_now_count: number;
  highest_priority_scope?: RuntimeTuningContextSnapshot['source_scope'] | null;
  most_recent_changed_scope?: RuntimeTuningContextSnapshot['source_scope'] | null;
  ordered_scopes: RuntimeTuningAlertSummaryScope[];
  summary: string;
};

export type RuntimeTuningReviewPriority = RuntimeTuningAlertStatus;
export type RuntimeTuningManualReviewStatus = 'UNREVIEWED' | 'ACKNOWLEDGED_CURRENT' | 'FOLLOWUP_REQUIRED' | 'STALE_REVIEW';
export type RuntimeTuningReviewReasonCode =
  | 'PROFILE_SHIFT'
  | 'GUARDRAIL_CHANGE'
  | 'EFFECTIVE_VALUE_CHANGE'
  | 'MULTI_FIELD_CHANGE'
  | 'NO_COMPARABLE_DIFF'
  | 'NO_CORRELATED_RUN'
  | 'STABLE_NO_ACTION';
export type RuntimeTuningReviewNextAction = 'OPEN_LATEST_DIFF' | 'CHECK_CORRELATED_RUN' | 'MONITOR_ONLY' | 'NO_ACTION_REQUIRED';

export type RuntimeTuningReviewBoardRow = {
  source_scope: RuntimeTuningContextSnapshot['source_scope'];
  review_status: RuntimeTuningManualReviewStatus;
  review_summary: string;
  alert_status: RuntimeTuningAlertStatus;
  drift_status: RuntimeTuningDriftStatus;
  attention_priority: RuntimeTuningReviewPriority;
  attention_rank: number;
  latest_diff_snapshot_id: number | null;
  latest_diff_status: RuntimeTuningDriftStatus | null;
  latest_diff_summary: string | null;
  correlated_run_id: number | null;
  correlated_run_timestamp: string | null;
  correlated_profile_name: string | null;
  correlated_profile_fingerprint: string | null;
  changed_field_count: number;
  changed_guardrail_count: number;
  review_reason_codes: RuntimeTuningReviewReasonCode[];
  recommended_next_action: RuntimeTuningReviewNextAction;
  board_summary: string;
};

export type RuntimeTuningReviewBoardQuery = {
  source_scope?: RuntimeTuningContextSnapshot['source_scope'];
  attention_only?: boolean;
  limit?: number;
};

export type RuntimeTuningInvestigationPacket = {
  source_scope: RuntimeTuningContextSnapshot['source_scope'];
  attention_priority: RuntimeTuningReviewPriority;
  attention_rank: number;
  alert_status: RuntimeTuningAlertStatus;
  drift_status: RuntimeTuningDriftStatus;
  board_summary: string;
  review_reason_codes: RuntimeTuningReviewReasonCode[];
  recommended_next_action: RuntimeTuningReviewNextAction;
  investigation_summary: string;

  latest_diff_snapshot_id: number | null;
  latest_diff_status: RuntimeTuningDriftStatus | null;
  latest_diff_summary: string | null;
  changed_field_count: number;
  changed_guardrail_count: number;
  changed_fields_preview: string[];
  changed_guardrail_fields_preview: string[];
  changed_fields_remaining_count: number;
  changed_guardrail_remaining_count: number;

  correlated_run_id: number | null;
  correlated_run_timestamp: string | null;
  correlated_profile_name: string | null;
  correlated_profile_fingerprint: string | null;
  correlated_run_summary: string | null;

  latest_snapshot_id: number;
  latest_snapshot_created_at: string;
  previous_snapshot_id: number | null;
  has_comparable_diff: boolean;
  has_correlated_run: boolean;

  runtime_deep_link: string;
  runtime_diff_deep_link: string;
};



export type RuntimeTuningScopeTimelineEntry = {
  snapshot_id: number;
  created_at: string;
  drift_status: RuntimeTuningDriftStatus;
  alert_status: RuntimeTuningAlertStatus;
  profile_name: string;
  profile_fingerprint: string | null;
  diff_summary: string;
  has_comparable_diff: boolean;
  changed_field_count: number;
  changed_guardrail_count: number;
  correlated_run_id: number | null;
  correlated_run_timestamp: string | null;
  timeline_reason_codes: string[];
  timeline_label: 'STABLE_BASELINE' | 'MINOR_CONTEXT_UPDATE' | 'PROFILE_SHIFT' | 'REVIEW_NOW' | 'INITIAL_SNAPSHOT';
};

export type RuntimeTuningScopeTimeline = {
  source_scope: RuntimeTuningContextSnapshot['source_scope'];
  entry_count: number;
  latest_snapshot_id: number;
  latest_snapshot_created_at: string;
  timeline_summary: string;
  is_recently_stable: boolean;
  has_recent_profile_shift: boolean;
  has_recent_review_now: boolean;
  entries: RuntimeTuningScopeTimelineEntry[];
};

export type RuntimeTuningScopeTimelineQuery = {
  limit?: number;
  include_stable?: boolean;
};

export type RuntimeTuningCockpitPanelItem = {
  source_scope: RuntimeTuningContextSnapshot['source_scope'];
  attention_priority: RuntimeTuningReviewPriority;
  attention_rank: number;
  alert_status: RuntimeTuningAlertStatus;
  drift_status: RuntimeTuningDriftStatus;
  board_summary: string;
  recommended_next_action: RuntimeTuningReviewNextAction;
  latest_diff_snapshot_id: number | null;
  latest_diff_status: RuntimeTuningDriftStatus | null;
  latest_diff_summary: string | null;
  correlated_run_id: number | null;
  correlated_run_timestamp: string | null;
  correlated_profile_name: string | null;
  correlated_profile_fingerprint: string | null;
  runtime_deep_link: string;
};

export type RuntimeTuningCockpitPanel = {
  generated_at: string;
  total_scope_count: number;
  attention_scope_count: number;
  highest_priority_scope: RuntimeTuningContextSnapshot['source_scope'] | null;
  highest_priority_status: RuntimeTuningReviewPriority | null;
  panel_summary: string;
  items: RuntimeTuningCockpitPanelItem[];
};

export type RuntimeTuningCockpitPanelDetail = RuntimeTuningCockpitPanelItem & {
  review_reason_codes: RuntimeTuningReviewReasonCode[];
  changed_field_count: number;
  changed_guardrail_count: number;
};

export type RuntimeTuningCockpitPanelQuery = {
  source_scope?: RuntimeTuningContextSnapshot['source_scope'];
  attention_only?: boolean;
  limit?: number;
};

export type RuntimePostureRun = {
  id: number;
  started_at: string;
  completed_at: string | null;
  considered_signal_count: number;
  mode_kept_count: number;
  mode_switch_count: number;
  caution_count: number;
  monitor_only_count: number;
  recovery_mode_count: number;
  throttled_count: number;
  blocked_count: number;
  recommendation_summary: Record<string, unknown>;
  metadata: Record<string, unknown>;
};

export type RuntimePostureSnapshot = {
  id: number;
  exposure_pressure_state: string;
  admission_pressure_state: string;
  session_health_state: string;
  recent_loss_state: string;
  signal_quality_state: string;
  runtime_posture: string;
  safety_posture: string;
  incident_pressure_state: string;
  portfolio_pressure_state: string;
  snapshot_summary: string;
  reason_codes: string[];
  metadata: Record<string, unknown>;
  created_at_snapshot: string;
};

export type OperatingModeDecision = {
  id: number;
  current_mode: GlobalOperatingMode | null;
  target_mode: GlobalOperatingMode;
  decision_type: string;
  decision_status: string;
  auto_applicable: boolean;
  decision_summary: string;
  reason_codes: string[];
  metadata: Record<string, unknown>;
  created_at_decision: string;
};

export type OperatingModeSwitchRecord = {
  id: number;
  previous_mode: GlobalOperatingMode | null;
  applied_mode: GlobalOperatingMode;
  switch_status: string;
  switch_summary: string;
  metadata: Record<string, unknown>;
  created_at_switch: string;
};

export type OperatingModeRecommendation = {
  id: number;
  recommendation_type: string;
  rationale: string;
  reason_codes: string[];
  confidence: number;
  blockers: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type OperatingModeSummary = RuntimeSummaryTuningContext & {
  latest_run_id: number | null;
  latest_decision_id: number | null;
  active_mode: GlobalOperatingMode;
  posture_reviews: number;
  mode_kept: number;
  mode_switched: number;
  caution_count: number;
  monitor_only_count: number;
  recovery_mode_count: number;
  throttled_count: number;
  blocked_count: number;
  governance_backlog_pressure_state: 'NORMAL' | 'CAUTION' | 'HIGH' | 'CRITICAL';
  recommendation_summary: Record<string, unknown>;
};


export type ModeEnforcementRun = {
  id: number;
  started_at: string;
  completed_at: string | null;
  current_mode: GlobalOperatingMode;
  considered_module_count: number;
  affected_module_count: number;
  restricted_module_count: number;
  throttled_module_count: number;
  blocked_module_count: number;
  monitor_only_module_count: number;
  recommendation_summary: Record<string, unknown>;
  metadata: Record<string, unknown>;
};

export type ModeModuleImpact = {
  id: number;
  linked_enforcement_run: number;
  current_mode: GlobalOperatingMode;
  module_name: string;
  impact_status: string;
  effective_behavior_summary: string;
  reason_codes: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type ModeEnforcementDecision = {
  id: number;
  linked_enforcement_run: number;
  module_name: string;
  decision_type: string;
  decision_status: string;
  auto_applicable: boolean;
  decision_summary: string;
  reason_codes: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type ModeEnforcementRecommendation = {
  id: number;
  target_enforcement_run: number | null;
  recommendation_type: string;
  rationale: string;
  reason_codes: string[];
  confidence: number;
  blockers: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type ModeEnforcementSummary = RuntimeSummaryTuningContext & {
  latest_run_id: number | null;
  current_mode: GlobalOperatingMode;
  modules_affected: number;
  reduced_count: number;
  throttled_count: number;
  monitor_only_count: number;
  blocked_count: number;
  recommendation_summary: Record<string, unknown>;
};

export type RuntimeFeedbackRun = {
  id: number;
  started_at: string;
  completed_at: string | null;
  considered_metric_count: number;
  healthy_runtime_count: number;
  overtrading_alert_count: number;
  quiet_runtime_alert_count: number;
  loss_pressure_alert_count: number;
  blocked_runtime_alert_count: number;
  feedback_decision_count: number;
  recommendation_summary: Record<string, unknown>;
  metadata: Record<string, unknown>;
};

export type RuntimePerformanceSnapshot = {
  id: number;
  linked_feedback_run: number | null;
  current_global_mode: GlobalOperatingMode;
  recent_dispatch_count: number;
  recent_closed_outcome_count: number;
  recent_loss_count: number;
  recent_no_action_tick_count: number;
  recent_blocked_tick_count: number;
  recent_deferred_dispatch_count: number;
  recent_parked_session_count: number;
  recent_exposure_throttle_count: number;
  recent_recovery_resume_count: number;
  signal_quality_state: 'STRONG' | 'NORMAL' | 'WEAK' | 'QUIET';
  runtime_pressure_state: 'NORMAL' | 'CAUTION' | 'HIGH' | 'CRITICAL';
  snapshot_summary: string;
  reason_codes: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type RuntimeDiagnosticReview = {
  id: number;
  linked_performance_snapshot: number;
  diagnostic_type: string;
  diagnostic_severity: 'INFO' | 'CAUTION' | 'HIGH' | 'CRITICAL';
  diagnostic_summary: string;
  reason_codes: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type RuntimeFeedbackDecision = {
  id: number;
  linked_performance_snapshot: number;
  linked_diagnostic_review: number;
  decision_type: string;
  decision_status: 'PROPOSED' | 'APPLIED' | 'SKIPPED' | 'BLOCKED';
  auto_applicable: boolean;
  decision_summary: string;
  reason_codes: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type RuntimeFeedbackRecommendation = {
  id: number;
  recommendation_type: string;
  target_feedback_run: number | null;
  target_diagnostic_review: number | null;
  target_feedback_decision: number | null;
  rationale: string;
  reason_codes: string[];
  confidence: number;
  blockers: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type RuntimeFeedbackSummary = RuntimeSummaryTuningContext & {
  latest_run_id: number | null;
  latest_snapshot_id: number | null;
  latest_decision_id: number | null;
  current_mode: GlobalOperatingMode;
  recent_dispatches: number;
  recent_losses: number;
  no_action_pressure: number;
  blocked_pressure: number;
  governance_backlog_pressure_state: 'NORMAL' | 'CAUTION' | 'HIGH' | 'CRITICAL';
  feedback_runs: number;
  feedback_decisions: number;
  applied_decisions: number;
  manual_review_required: number;
  recommendation_summary: Record<string, unknown>;
};

export type RuntimeFeedbackApplyRun = {
  id: number;
  started_at: string;
  completed_at: string | null;
  considered_feedback_decision_count: number;
  applied_count: number;
  manual_review_count: number;
  blocked_count: number;
  mode_switch_count: number;
  enforcement_refresh_count: number;
  recommendation_summary: Record<string, unknown>;
  metadata: Record<string, unknown>;
};

export type RuntimeFeedbackApplyDecision = {
  id: number;
  linked_feedback_decision: number;
  linked_apply_run: number | null;
  current_mode: GlobalOperatingMode | null;
  target_mode: GlobalOperatingMode | null;
  apply_type: string;
  apply_status: 'PROPOSED' | 'APPLIED' | 'SKIPPED' | 'BLOCKED';
  auto_applicable: boolean;
  apply_summary: string;
  reason_codes: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type RuntimeFeedbackApplyRecord = {
  id: number;
  linked_apply_decision: number;
  record_status: 'APPLIED' | 'SKIPPED' | 'BLOCKED' | 'FAILED';
  previous_mode: GlobalOperatingMode | null;
  applied_mode: GlobalOperatingMode | null;
  enforcement_refreshed: boolean;
  record_summary: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type RuntimeFeedbackApplyRecommendation = {
  id: number;
  recommendation_type: string;
  target_feedback_decision: number | null;
  target_apply_decision: number | null;
  rationale: string;
  reason_codes: string[];
  confidence: number;
  blockers: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type RuntimeFeedbackApplySummary = {
  latest_run_id: number | null;
  latest_apply_decision_id: number | null;
  latest_apply_record_id: number | null;
  apply_runs: number;
  apply_decisions: number;
  apply_records: number;
  recommendations: number;
  applied_count: number;
  manual_review_count: number;
  blocked_count: number;
  enforcement_refresh_count: number;
  recommendation_summary: Record<string, unknown>;
};

export type RuntimeModeStabilizationRun = {
  id: number;
  started_at: string;
  completed_at: string | null;
  considered_transition_count: number;
  allowed_count: number;
  deferred_count: number;
  dwell_hold_count: number;
  blocked_count: number;
  manual_review_count: number;
  recommendation_summary: Record<string, unknown>;
  metadata: Record<string, unknown>;
};

export type RuntimeModeTransitionSnapshot = {
  id: number;
  linked_run: number | null;
  linked_feedback_decision: number | null;
  current_mode: GlobalOperatingMode;
  target_mode: GlobalOperatingMode;
  current_mode_started_at: string | null;
  time_in_current_mode_seconds: number;
  recent_switch_count: number;
  recent_switch_window_seconds: number;
  last_switch_at: string | null;
  feedback_pressure_state: 'LOW' | 'NORMAL' | 'HIGH' | 'CRITICAL';
  transition_risk_state: 'LOW' | 'CAUTION' | 'HIGH' | 'CRITICAL';
  snapshot_summary: string;
  reason_codes: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type RuntimeModeStabilityReview = {
  id: number;
  linked_transition_snapshot: number;
  review_type: string;
  review_severity: 'INFO' | 'CAUTION' | 'HIGH' | 'CRITICAL';
  review_summary: string;
  reason_codes: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type RuntimeModeTransitionDecision = {
  id: number;
  linked_transition_snapshot: number;
  linked_stability_review: number;
  decision_type: string;
  decision_status: 'PROPOSED' | 'SKIPPED' | 'BLOCKED';
  auto_applicable: boolean;
  decision_summary: string;
  reason_codes: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type RuntimeModeTransitionApplyRecord = {
  id: number;
  linked_transition_decision: number;
  apply_status: 'APPLIED' | 'SKIPPED' | 'BLOCKED' | 'FAILED';
  previous_mode: GlobalOperatingMode | null;
  applied_mode: GlobalOperatingMode | null;
  enforcement_refreshed: boolean;
  apply_summary: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type RuntimeModeStabilizationRecommendation = {
  id: number;
  target_transition_snapshot: number | null;
  target_stability_review: number | null;
  target_transition_decision: number | null;
  recommendation_type: string;
  rationale: string;
  reason_codes: string[];
  confidence: number;
  blockers: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type RuntimeModeStabilizationSummary = RuntimeSummaryTuningContext & {
  latest_run_id: number | null;
  latest_snapshot_id: number | null;
  latest_review_id: number | null;
  latest_decision_id: number | null;
  latest_apply_record_id: number | null;
  runs: number;
  snapshots: number;
  reviews: number;
  decisions: number;
  recommendations: number;
  apply_records: number;
  allowed_count: number;
  deferred_count: number;
  dwell_hold_count: number;
  blocked_count: number;
  manual_review_count: number;
  applied_count: number;
  blocked_apply_count: number;
  recommendation_summary: Record<string, unknown>;
};

export type RuntimeTuningProfileSummary = {
  profile_name: string;
  backlog_thresholds: Record<string, number>;
  backlog_weights: Record<string, number>;
  feedback_guardrails: Record<string, string | number | boolean>;
  operating_mode_guardrails: Record<string, string | number | boolean>;
  stabilization_guardrails: Record<string, string | number | boolean>;
  effective_values: {
    high_backlog_manual_review_bias: boolean;
    critical_backlog_monitor_only_bias: boolean;
    critical_backlog_blocks_relax: boolean;
    high_backlog_relax_dwell_multiplier: number;
    critical_backlog_relax_dwell_multiplier: number;
  };
  summary: string;
  created_at: string | null;
};


export type RuntimeTuningReviewState = {
  source_scope: RuntimeTuningContextSnapshot['source_scope'];
  effective_review_status: RuntimeTuningManualReviewStatus;
  stored_review_status: RuntimeTuningManualReviewStatus;
  latest_snapshot_id: number;
  last_reviewed_snapshot_id: number | null;
  has_newer_snapshot_than_reviewed: boolean;
  last_action_type: string;
  last_action_at: string | null;
  review_summary: string;
  runtime_deep_link: string;
  runtime_investigation_deep_link: string;
};



export type RuntimeTuningReviewQueueReasonCode =
  | 'FOLLOWUP_REQUIRED'
  | 'STALE_REVIEW'
  | 'UNREVIEWED_SCOPE'
  | 'TECHNICAL_REVIEW_NOW'
  | 'TECHNICAL_PROFILE_SHIFT'
  | 'TECHNICAL_MINOR_CHANGE'
  | 'ACKNOWLEDGED_CURRENT';

export type RuntimeTuningReviewQueueItem = {
  source_scope: RuntimeTuningContextSnapshot['source_scope'];
  effective_review_status: RuntimeTuningManualReviewStatus;
  attention_priority: RuntimeTuningReviewPriority;
  queue_rank: number;
  requires_manual_attention: boolean;
  queue_reason_codes: RuntimeTuningReviewQueueReasonCode[];
  technical_summary: string;
  review_summary: string;
  last_action_type: string;
  last_action_at: string | null;
  has_newer_snapshot_than_reviewed: boolean;
  runtime_deep_link: string;
  runtime_investigation_deep_link: string;
  latest_snapshot_id?: number | null;
  last_reviewed_snapshot_id?: number | null;
};

export type RuntimeTuningReviewQueue = {
  total_scope_count: number;
  queue_count: number;
  unreviewed_count: number;
  followup_count: number;
  stale_count: number;
  highest_priority_scope: RuntimeTuningContextSnapshot['source_scope'] | null;
  queue_summary: string;
  items: RuntimeTuningReviewQueueItem[];
};

export type RuntimeTuningReviewQueueDetail = RuntimeTuningReviewQueueItem & {
  stored_review_status: RuntimeTuningManualReviewStatus;
  queue_summary: string;
};

export type RuntimeTuningReviewQueueQuery = {
  unresolved_only?: boolean;
  effective_review_status?: RuntimeTuningManualReviewStatus;
  limit?: number;
};

export type RuntimeTuningReviewAgingBucket = 'FRESH' | 'AGING' | 'OVERDUE';

export type RuntimeTuningReviewAgingReasonCode =
  | 'FOLLOWUP_AGING'
  | 'FOLLOWUP_OVERDUE'
  | 'STALE_REVIEW_PENDING'
  | 'STALE_REVIEW_OVERDUE'
  | 'UNREVIEWED_AGING'
  | 'UNREVIEWED_OVERDUE'
  | 'ACKNOWLEDGED_NOT_URGENT';

export type RuntimeTuningReviewAgingItem = RuntimeTuningReviewQueueItem & {
  age_bucket: RuntimeTuningReviewAgingBucket;
  age_days: number;
  overdue: boolean;
  aging_rank: number;
  aging_reason_codes: RuntimeTuningReviewAgingReasonCode[];
  age_reference_timestamp: string | null;
};

export type RuntimeTuningReviewAging = {
  queue_count: number;
  fresh_count: number;
  aging_count: number;
  overdue_count: number;
  highest_urgency_scope: RuntimeTuningContextSnapshot['source_scope'] | null;
  aging_summary: string;
  items: RuntimeTuningReviewAgingItem[];
};

export type RuntimeTuningReviewAgingDetail = RuntimeTuningReviewAgingItem & {
  aging_summary: string;
};

export type RuntimeTuningReviewAgingQuery = {
  unresolved_only?: boolean;
  age_bucket?: RuntimeTuningReviewAgingBucket;
  limit?: number;
};

export type RuntimeTuningReviewEscalationLevel = 'MONITOR' | 'ELEVATED' | 'URGENT';

export type RuntimeTuningReviewEscalationReasonCode =
  | 'FOLLOWUP_OVERDUE'
  | 'STALE_OVERDUE'
  | 'UNREVIEWED_REVIEW_NOW_OVERDUE'
  | 'FOLLOWUP_AGING'
  | 'STALE_AGING'
  | 'UNREVIEWED_OVERDUE'
  | 'UNREVIEWED_PROFILE_SHIFT'
  | 'MONITOR_ONLY';

export type RuntimeTuningReviewEscalationItem = RuntimeTuningReviewAgingItem & {
  escalation_level: RuntimeTuningReviewEscalationLevel;
  escalation_rank: number;
  requires_immediate_attention: boolean;
  escalation_reason_codes: RuntimeTuningReviewEscalationReasonCode[];
};

export type RuntimeTuningReviewEscalation = {
  queue_count: number;
  escalated_count: number;
  urgent_count: number;
  elevated_count: number;
  monitor_count: number;
  highest_escalation_scope: RuntimeTuningContextSnapshot['source_scope'] | null;
  escalation_summary: string;
  items: RuntimeTuningReviewEscalationItem[];
};

export type RuntimeTuningReviewEscalationDetail = RuntimeTuningReviewEscalationItem & {
  escalation_summary: string;
};

export type RuntimeTuningReviewEscalationQuery = {
  escalated_only?: boolean;
  escalation_level?: RuntimeTuningReviewEscalationLevel;
  limit?: number;
};

export type RuntimeTuningReviewStateQuery = {
  source_scope?: RuntimeTuningContextSnapshot['source_scope'];
  effective_status?: RuntimeTuningManualReviewStatus;
  needs_attention?: boolean;
};

export type RuntimeTuningReviewAction = {
  id: number;
  source_scope: RuntimeTuningContextSnapshot['source_scope'];
  action_type: 'ACKNOWLEDGE_CURRENT' | 'MARK_FOLLOWUP_REQUIRED' | 'CLEAR_REVIEW_STATE';
  snapshot_id: number | null;
  resulting_review_status: RuntimeTuningManualReviewStatus;
  created_at: string;
};

export type RuntimeTuningReviewActivityLabel = 'ACKNOWLEDGED' | 'FOLLOWUP_MARKED' | 'REVIEW_CLEARED';

export type RuntimeTuningReviewActivityReasonCode =
  | 'ACTION_ACKNOWLEDGE_CURRENT'
  | 'ACTION_MARK_FOLLOWUP_REQUIRED'
  | 'ACTION_CLEAR_REVIEW_STATE'
  | 'STATE_NOW_ACKNOWLEDGED'
  | 'STATE_NOW_FOLLOWUP'
  | 'STATE_NOW_UNREVIEWED';

export type RuntimeTuningReviewActivityItem = {
  source_scope: RuntimeTuningContextSnapshot['source_scope'];
  action_type: RuntimeTuningReviewAction['action_type'];
  created_at: string;
  resulting_review_status: RuntimeTuningManualReviewStatus;
  snapshot_id: number | null;
  activity_label: RuntimeTuningReviewActivityLabel;
  activity_reason_codes: RuntimeTuningReviewActivityReasonCode[];
  scope_review_summary: string;
  runtime_investigation_deep_link: string;
  effective_review_status?: RuntimeTuningManualReviewStatus;
  has_newer_snapshot_than_reviewed?: boolean;
};

export type RuntimeTuningReviewActivity = {
  activity_count: number;
  latest_action_at: string | null;
  activity_summary: string;
  items: RuntimeTuningReviewActivityItem[];
};

export type RuntimeTuningReviewActivityDetail = {
  source_scope: RuntimeTuningContextSnapshot['source_scope'];
  activity_count: number;
  latest_action_at: string;
  scope_activity_summary: string;
  items: RuntimeTuningReviewActivityItem[];
};

export type RuntimeTuningReviewActivityQuery = {
  source_scope?: RuntimeTuningContextSnapshot['source_scope'];
  action_type?: RuntimeTuningReviewAction['action_type'];
  limit?: number;
};


export type RuntimeTuningAutotriageHumanAttentionMode = 'REVIEW_NOW' | 'REVIEW_SOON' | 'MONITOR_ONLY' | 'NO_ACTION';

export type RuntimeTuningAutotriageReasonCode =
  | 'URGENT_SCOPE_PRESENT'
  | 'OVERDUE_SCOPE_PRESENT'
  | 'FOLLOWUP_PENDING'
  | 'STALE_REVIEW_PENDING'
  | 'RECENT_ACTIVITY_ONLY'
  | 'NO_UNRESOLVED_SCOPES';

export type RuntimeTuningAutotriageTopScope = {
  source_scope: RuntimeTuningContextSnapshot['source_scope'];
  effective_review_status: RuntimeTuningManualReviewStatus;
  attention_priority: RuntimeTuningReviewPriority;
  age_bucket: RuntimeTuningReviewAgingBucket;
  escalation_level: RuntimeTuningReviewEscalationLevel;
  requires_immediate_attention: boolean;
  review_summary: string;
  technical_summary: string;
  runtime_investigation_deep_link: string;
  age_days?: number | null;
  last_action_at?: string | null;
};

export type RuntimeTuningAutotriageDigest = {
  generated_at: string;
  human_attention_mode: RuntimeTuningAutotriageHumanAttentionMode;
  requires_human_now: boolean;
  can_defer_human_review: boolean;
  unresolved_count: number;
  urgent_count: number;
  overdue_count: number;
  recent_activity_count: number;
  next_recommended_scope: RuntimeTuningContextSnapshot['source_scope'] | null;
  next_recommended_reason_codes: RuntimeTuningAutotriageReasonCode[];
  autotriage_summary: string;
  top_scopes: RuntimeTuningAutotriageTopScope[];
};

export type RuntimeTuningAutotriageDetail = RuntimeTuningAutotriageTopScope & {
  generated_at: string;
  human_attention_mode: RuntimeTuningAutotriageHumanAttentionMode;
  next_recommended_scope: RuntimeTuningContextSnapshot['source_scope'] | null;
  next_recommended_reason_codes: RuntimeTuningAutotriageReasonCode[];
};

export type RuntimeTuningAutotriageQuery = {
  top_n?: number;
  include_monitor?: boolean;
};

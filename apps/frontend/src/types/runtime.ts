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

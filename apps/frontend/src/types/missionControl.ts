export type MissionControlStatus = 'IDLE' | 'RUNNING' | 'PAUSED' | 'DEGRADED' | 'STOPPED' | 'FAILED';
export type MissionControlCycleStatus = 'SUCCESS' | 'PARTIAL' | 'FAILED' | 'SKIPPED';

export type MissionControlStep = {
  id: number;
  step_type: string;
  status: MissionControlCycleStatus;
  started_at: string;
  finished_at: string | null;
  summary: string;
  details: Record<string, unknown>;
};

export type MissionControlCycle = {
  id: number;
  session: number;
  cycle_number: number;
  status: MissionControlCycleStatus;
  started_at: string;
  finished_at: string | null;
  steps_run_count: number;
  opportunities_built: number;
  proposals_generated: number;
  queue_count: number;
  auto_execute_count: number;
  blocked_count: number;
  summary: string;
  details: Record<string, unknown>;
  steps: MissionControlStep[];
};

export type MissionControlSession = {
  id: number;
  status: MissionControlStatus;
  started_at: string;
  finished_at: string | null;
  cycle_count: number;
  last_cycle_at: string | null;
  summary: string;
  metadata: Record<string, unknown>;
};

export type MissionControlState = {
  id: number;
  status: MissionControlStatus;
  active_session: number | null;
  pause_requested: boolean;
  stop_requested: boolean;
  cycle_in_progress: boolean;
  last_heartbeat_at: string | null;
  last_error: string;
  profile_slug: string;
  settings_snapshot: Record<string, unknown>;
};

export type AutonomousRuntimeRun = {
  id: number;
  started_at: string;
  completed_at: string | null;
  runtime_status: string;
  cycle_count: number;
  executed_cycle_count: number;
  blocked_cycle_count: number;
  dispatch_count: number;
  closed_outcome_count: number;
  postmortem_handoff_count: number;
  learning_handoff_count: number;
  reuse_applied_count: number;
  recommendation_summary: string;
  metadata: Record<string, unknown>;
};

export type AutonomousCyclePlan = {
  id: number;
  linked_runtime_run: number;
  planned_step_flags: Record<string, boolean>;
  plan_status: string;
  runtime_mode: string;
  portfolio_posture: string;
  safety_posture: string;
  degraded_mode_state: string;
  plan_summary: string;
  reason_codes: string[];
};

export type AutonomousCycleExecution = {
  id: number;
  linked_cycle_plan: number;
  execution_status: string;
  executed_steps: string[];
  skipped_steps: string[];
  blocked_steps: string[];
  execution_summary: string;
};

export type AutonomousCycleOutcome = {
  id: number;
  linked_cycle_execution: number;
  outcome_status: string;
  dispatch_count: number;
  watch_update_count: number;
  close_action_count: number;
  postmortem_count: number;
  learning_count: number;
  reuse_count: number;
  outcome_summary: string;
};

export type AutonomousRuntimeRecommendation = {
  id: number;
  recommendation_type: string;
  rationale: string;
  reason_codes: string[];
  confidence: number;
  blockers: string[];
};

export type MissionControlStatusResponse = {
  state: MissionControlState;
  active_session: MissionControlSession | null;
  latest_cycle: MissionControlCycle | null;
  profiles: Array<{ slug: string; label: string }>;
  runtime: { current_mode: string; status: string };
  safety: { status: string; status_message?: string; kill_switch_enabled: boolean; hard_stop_active: boolean };
};

export type MissionControlSummary = {
  latest_session: MissionControlSession | null;
  latest_cycle: MissionControlCycle | null;
  session_count: number;
  cycle_count: number;
};

export type LivePaperBootstrapRequest = {
  preset?: string;
  auto_start_heartbeat?: boolean;
  start_now?: boolean;
};

export type LivePaperBootstrapResponse = {
  preset_name: string;
  session_created: boolean;
  session_started: boolean;
  heartbeat_started: boolean;
  runtime_mode: string;
  paper_execution_mode: string;
  market_data_mode: string;
  bootstrap_action: 'CREATED_AND_STARTED' | 'STARTED_EXISTING_SAFE_SESSION' | 'REUSED_EXISTING_SESSION' | 'BLOCKED' | 'FAILED';
  session_id: number | null;
  next_step_summary: string;
  bootstrap_summary: string;
  stack_snapshot?: Record<string, unknown>;
};

export type LivePaperBootstrapStatusResponse = {
  preset_name: string;
  session_active: boolean;
  heartbeat_active: boolean;
  runtime_mode: string;
  market_data_mode: string;
  paper_execution_mode: string;
  current_session_status: string;
  operator_attention_hint: string;
  status_summary: string;
};

export type LivePaperAttentionMode = 'HEALTHY' | 'DEGRADED' | 'REVIEW_NOW' | 'BLOCKED';
export type LivePaperAttentionAlertAction = 'CREATED' | 'UPDATED' | 'RESOLVED' | 'NOOP';
export type LivePaperAttentionSyncAction = LivePaperAttentionAlertAction | 'ERROR' | null;
export type LivePaperAttentionSeverity = 'warning' | 'high' | 'critical' | null;
export type LivePaperFunnelStatus = 'ACTIVE' | 'THIN_FLOW' | 'STALLED';
export type LivePaperFunnelStage = 'scan' | 'research' | 'prediction' | 'risk' | 'paper_execution';

export type LivePaperAttentionAutoSyncStatus = {
  attempted: boolean;
  success: boolean;
  alert_action: LivePaperAttentionSyncAction;
  attention_mode: LivePaperAttentionMode | null;
  session_active?: boolean;
  heartbeat_active?: boolean;
  current_session_status?: string | null;
  sync_summary: string;
};

export type LivePaperAttentionAlertStatusResponse = {
  attention_needed: boolean;
  attention_mode: LivePaperAttentionMode;
  active_alert_present: boolean;
  active_alert_severity: LivePaperAttentionSeverity;
  session_active: boolean;
  heartbeat_active: boolean;
  current_session_status: string;
  status_summary: string;
  funnel_status?: LivePaperFunnelStatus | null;
  stalled_stage?: LivePaperFunnelStage | null;
  top_stage?: LivePaperFunnelStage | null;
  funnel_summary?: string | null;
  last_alert_action?: LivePaperAttentionSyncAction;
  last_sync_summary?: string | null;
  last_auto_sync?: LivePaperAttentionAutoSyncStatus | null;
};


export type LivePaperValidationCheck = {
  check_name: string;
  status: 'PASS' | 'WARN' | 'FAIL';
  summary: string;
};

export type LivePaperValidationDigestResponse = {
  preset_name: string;
  validation_status: 'READY' | 'WARNING' | 'BLOCKED';
  session_active: boolean;
  heartbeat_active: boolean;
  attention_mode: LivePaperAttentionMode;
  paper_account_ready: boolean;
  market_data_ready: boolean;
  portfolio_snapshot_ready: boolean;
  recent_activity_present: boolean;
  recent_trades_present: boolean;
  cash_available: number | null;
  equity_available: number | null;
  next_action_hint: string;
  validation_summary: string;
  checks: LivePaperValidationCheck[];
};

export type LivePaperSmokeTestStatus = 'PASS' | 'WARN' | 'FAIL';

export type LivePaperSmokeTestCheck = {
  check_name: string;
  status: LivePaperSmokeTestStatus;
  summary: string;
};

export type LivePaperSmokeTestRequest = {
  preset?: string;
  heartbeat_passes?: 1 | 2;
};

export type LivePaperSmokeTestResultResponse = {
  preset_name: string;
  smoke_test_status: LivePaperSmokeTestStatus;
  executed_at: string;
  bootstrap_action: string;
  session_active_after: boolean;
  heartbeat_active_after: boolean;
  validation_status_before: 'READY' | 'WARNING' | 'BLOCKED';
  validation_status_after: 'READY' | 'WARNING' | 'BLOCKED';
  heartbeat_passes_requested: number;
  heartbeat_passes_completed: number;
  recent_activity_detected: boolean;
  recent_trades_detected: boolean;
  next_action_hint: string;
  smoke_test_summary: string;
  checks: LivePaperSmokeTestCheck[];
};

export type LivePaperSmokeTestStatusResponse = {
  exists?: boolean;
  status?: 'AVAILABLE' | 'NO_RUN_YET' | string | null;
  summary?: string | null;
  reason_code?: string | null;
  preset_name: string;
  smoke_test_status: LivePaperSmokeTestStatus;
  executed_at: string;
  validation_status_after: 'READY' | 'WARNING' | 'BLOCKED';
  heartbeat_passes_completed: number;
  smoke_test_summary: string;
  next_action_hint: string;
};

export type LivePaperTrialRunRequest = {
  preset?: string;
  heartbeat_passes?: 1 | 2;
};

export type LivePaperTrialRunStatus = 'PASS' | 'WARN' | 'FAIL';

export type LivePaperTrialRunCheck = {
  check_name: string;
  status: LivePaperTrialRunStatus;
  summary: string;
};

export type LivePaperTrialRunResultResponse = {
  preset_name: string;
  trial_status: LivePaperTrialRunStatus;
  executed_at: string;
  bootstrap_action: string;
  smoke_test_status: LivePaperSmokeTestStatus;
  validation_status_before: 'READY' | 'WARNING' | 'BLOCKED';
  validation_status_after: 'READY' | 'WARNING' | 'BLOCKED';
  heartbeat_passes_requested: number;
  heartbeat_passes_completed: number;
  recent_activity_detected: boolean;
  recent_trades_detected: boolean;
  portfolio_snapshot_ready: boolean;
  next_action_hint: string;
  trial_summary: string;
  checks: LivePaperTrialRunCheck[];
};

export type LivePaperTrialRunStatusResponse = {
  exists?: boolean;
  status?: 'AVAILABLE' | 'NO_RUN_YET' | string | null;
  summary?: string | null;
  reason_code?: string | null;
  preset_name: string;
  trial_status: LivePaperTrialRunStatus;
  executed_at: string;
  smoke_test_status: LivePaperSmokeTestStatus;
  validation_status_after: 'READY' | 'WARNING' | 'BLOCKED';
  heartbeat_passes_completed: number;
  trial_summary: string;
  next_action_hint: string;
};

export type LivePaperTrialHistoryStatus = 'PASS' | 'WARN' | 'FAIL';

export type LivePaperTrialHistoryItem = {
  created_at: string;
  preset_name: string;
  trial_status: LivePaperTrialHistoryStatus;
  bootstrap_action: string;
  smoke_test_status: LivePaperSmokeTestStatus;
  validation_status_after: 'READY' | 'WARNING' | 'BLOCKED';
  heartbeat_passes_completed: number;
  next_action_hint: string;
  trial_summary: string;
  recent_activity_detected?: boolean;
  recent_trades_detected?: boolean;
  portfolio_snapshot_ready?: boolean;
};

export type LivePaperTrialHistoryResponse = {
  count: number;
  latest_trial_status: LivePaperTrialHistoryStatus | null;
  history_summary: string;
  items: LivePaperTrialHistoryItem[];
};

export type LivePaperTrialTrendStatus = 'IMPROVING' | 'STABLE' | 'DEGRADING' | 'INSUFFICIENT_DATA';
export type LivePaperTrialReadinessStatus = 'READY_FOR_EXTENDED_RUN' | 'NEEDS_REVIEW' | 'NOT_READY';

export type LivePaperTrialTrendCounts = {
  pass_count: number;
  warn_count: number;
  fail_count: number;
};

export type LivePaperTrialTrendResponse = {
  sample_size: number;
  latest_trial_status: LivePaperTrialHistoryStatus | null;
  latest_validation_status: 'READY' | 'WARNING' | 'BLOCKED' | null;
  trend_status: LivePaperTrialTrendStatus;
  readiness_status: LivePaperTrialReadinessStatus;
  trend_summary: string;
  next_action_hint: string;
  counts: LivePaperTrialTrendCounts;
  recent_statuses?: LivePaperTrialHistoryStatus[];
};

export type LivePaperExtendedRunGateStatus = 'ALLOW' | 'ALLOW_WITH_CAUTION' | 'BLOCK';

export type LivePaperExtendedRunGateCheck = {
  check_name: string;
  status: 'PASS' | 'WARN' | 'FAIL';
  summary: string;
};

export type LivePaperExtendedRunGateResponse = {
  preset_name: string;
  gate_status: LivePaperExtendedRunGateStatus;
  gate_summary: string;
  next_action_hint: string;
  latest_trial_status: LivePaperTrialHistoryStatus | null;
  trend_status: LivePaperTrialTrendStatus | null;
  readiness_status: LivePaperTrialReadinessStatus | null;
  validation_status: 'READY' | 'WARNING' | 'BLOCKED' | null;
  attention_mode: LivePaperAttentionMode | null;
  funnel_status: LivePaperAutonomyFunnelStatus | null;
  reason_codes?: string[];
  checks: LivePaperExtendedRunGateCheck[];
};

export type ExtendedPaperRunLaunchRequest = {
  preset?: string;
};

export type ExtendedPaperRunLaunchStatus =
  | 'STARTED'
  | 'REUSED_RUNNING_SESSION'
  | 'REUSED_PAUSED_SESSION'
  | 'BLOCKED'
  | 'FAILED';

export type ExtendedPaperRunLaunchResponse = {
  preset_name: string;
  launch_status: ExtendedPaperRunLaunchStatus;
  gate_status: LivePaperExtendedRunGateStatus;
  session_active: boolean;
  heartbeat_active: boolean;
  current_session_status: string;
  caution_mode?: boolean | null;
  next_action_hint: string;
  launch_summary: string;
  reason_codes: string[];
};

export type ExtendedPaperRunStatusResponse = {
  exists?: boolean;
  status?: 'AVAILABLE' | 'NO_RUN_YET' | string | null;
  summary?: string | null;
  reason_code?: string | null;
  preset_name: string;
  extended_run_active: boolean;
  gate_status: LivePaperExtendedRunGateStatus;
  session_active: boolean;
  heartbeat_active: boolean;
  current_session_status: string;
  caution_mode?: boolean | null;
  status_summary: string;
  next_action_hint: string;
};

export type LivePaperAutonomyFunnelStatus = 'ACTIVE' | 'THIN_FLOW' | 'STALLED';
export type LivePaperAutonomyFunnelStageStatus = 'ACTIVE' | 'LOW' | 'EMPTY';

export type LivePaperAutonomyFunnelStage = {
  stage_name: 'scan' | 'research' | 'prediction' | 'risk' | 'paper_execution';
  count: number;
  status: LivePaperAutonomyFunnelStageStatus;
  summary: string;
};

export type LivePaperAutonomyFunnelResponse = {
  window_minutes: number;
  preset_name: string;
  funnel_status: LivePaperAutonomyFunnelStatus;
  scan_count: number;
  research_count: number;
  prediction_count: number;
  risk_approved_count: number;
  risk_blocked_count: number;
  paper_execution_count: number;
  recent_trades_count: number;
  top_stage: LivePaperFunnelStage;
  stalled_stage: LivePaperFunnelStage | null;
  next_action_hint: string;
  funnel_summary: string;
  stages: LivePaperAutonomyFunnelStage[];
};

export type LivePaperAttentionAlertSyncResponse = {
  attention_needed: boolean;
  attention_mode: LivePaperAttentionMode;
  alert_action: LivePaperAttentionAlertAction;
  alert_severity?: LivePaperAttentionSeverity;
  session_active: boolean;
  heartbeat_active: boolean;
  current_session_status: string;
  attention_reason_codes?: string[];
  status_summary: string;
  alert_status_summary: string;
  material_change_detected?: boolean;
  material_change_fields?: string[];
  update_suppressed?: boolean;
  suppression_reason?: 'NO_MATERIAL_CHANGE' | 'ALERT_NOT_NEEDED' | 'NO_ACTIVE_ALERT' | null;
  active_alert_present?: boolean;
  funnel_status?: LivePaperFunnelStatus | null;
  stalled_stage?: LivePaperFunnelStage | null;
  top_stage?: LivePaperFunnelStage | null;
  funnel_summary?: string | null;
};

export type TestConsoleRunRequest = {
  preset?: string;
  heartbeat_passes?: 1 | 2;
  profile_id?: 'full_e2e' | 'scope_throttle_diagnostics' | 'prediction_risk_path' | 'exposure_diagnostics' | 'export_snapshot_integrity';
};

export type TestConsoleScanSummary = {
  summary?: string | null;
  count?: number | null;
};

export type TestConsolePortfolioSummary = {
  summary?: string | null;
  equity?: number | string | null;
  cash?: number | string | null;
  open_positions?: number | null;
};

export type LlmShadowSummary = {
  artifact_id?: number | null;
  provider?: string | null;
  model?: string | null;
  llm_shadow_reasoning_status?: string | null;
  stance?: string | null;
  confidence?: string | null;
  recommendation_mode?: string | null;
  summary?: string | null;
  key_risks?: string[];
  key_supporting_points?: string[];
  advisory_only?: boolean;
  affects_execution?: boolean;
  paper_only?: boolean;
  shadow_only?: boolean;
  non_blocking?: boolean;
  timestamp?: string | null;
};

export type LlmAuxSignalSummary = {
  enabled?: boolean;
  source_artifact_id?: number | null;
  aux_signal_status?: string | null;
  aux_signal_recommendation?: string | null;
  aux_signal_reason_codes?: string[];
  aux_signal_weight?: number | null;
  advisory_only?: boolean;
  affects_execution?: boolean;
  paper_only?: boolean;
  summary?: string | null;
};

export type TestConsoleStatusResponse = {
  test_status: string;
  test_profile?: string;
  available_test_profiles?: Record<string, Record<string, boolean>>;
  modules_included?: string[];
  modules_omitted?: string[];
  run_scope?: 'fresh_full_run' | 'targeted_diagnostic_run' | string;
  current_phase: string | null;
  current_step?: number | null;
  current_step_label?: string | null;
  completed_steps?: number | null;
  total_steps?: number | null;
  progress_state?: 'idle' | 'running' | 'completed' | 'blocked' | 'failed' | 'stopped' | string;
  started_at: string | null;
  updated_at?: string | null;
  last_progress_at?: string | null;
  last_real_progress_at?: string | null;
  last_non_progress_refresh_at?: string | null;
  phase_entered_at?: string | null;
  hang_detected_at?: string | null;
  hang_detection_reason?: string | null;
  hang_reason_classification?: string | null;
  stop_requested_at?: string | null;
  ended_at: string | null;
  elapsed_seconds?: number | null;
  last_event?: string | null;
  last_reason_code?: string | null;
  export_available?: boolean;
  is_stale?: boolean;
  is_terminal?: boolean;
  is_hung?: boolean;
  has_active_run?: boolean;
  has_last_completed_run?: boolean;
  current_run_id?: string | null;
  last_run_id?: string | null;
  can_stop?: boolean;
  stop_available?: boolean;
  can_stop_reason?: string | null;
  validation_status: string | null;
  trial_status: string | null;
  trend_status: string | null;
  readiness_status: string | null;
  gate_status: string | null;
  extended_run_status: string | null;
  attention_mode: string | null;
  funnel_status: string | null;
  scan_summary?: TestConsoleScanSummary | string | null;
  portfolio_summary?: TestConsolePortfolioSummary | string | null;
  llm_shadow_summary?: LlmShadowSummary | null;
  latest_llm_shadow_summary?: LlmShadowSummary | null;
  llm_shadow_history_count?: number;
  llm_shadow_recent_history?: LlmShadowSummary[];
  llm_aux_signal_summary?: LlmAuxSignalSummary | null;
  next_action_hint: string | null;
  blocker_summary?: string | null;
};

export type TestConsoleExportLogFormat = 'text' | 'json';

export type AutonomousRuntimeSummary = {
  latest_runtime_run_id: number | null;
  runtime_run_count: number;
  cycle_plan_count: number;
  cycle_execution_count: number;
  cycle_outcome_count: number;
  totals: {
    dispatch_count: number;
    closed_outcome_count: number;
    postmortem_handoff_count: number;
    learning_handoff_count: number;
    reuse_applied_count: number;
  };
};

export type AutonomousRuntimeSession = {
  id: number;
  started_at: string;
  stopped_at: string | null;
  session_status: 'RUNNING' | 'PAUSED' | 'STOPPED' | 'DEGRADED' | 'BLOCKED' | 'COMPLETED';
  runtime_mode: string;
  profile_slug: string;
  tick_count: number;
  executed_tick_count: number;
  skipped_tick_count: number;
  dispatch_count: number;
  closed_outcome_count: number;
  pause_reason_codes: string[];
  stop_reason_codes: string[];
  metadata: Record<string, unknown>;
  updated_at: string;
};

export type AutonomousRuntimeTick = {
  id: number;
  linked_session: number;
  tick_index: number;
  planned_tick_mode: string;
  tick_status: string;
  linked_runtime_run: number | null;
  linked_cycle_plan: number | null;
  linked_cycle_execution: number | null;
  linked_cycle_outcome: number | null;
  tick_summary: string;
  reason_codes: string[];
};

export type AutonomousCadenceDecision = {
  id: number;
  linked_session: number;
  linked_previous_tick: number | null;
  cadence_mode: string;
  cadence_reason_codes: string[];
  portfolio_posture: string;
  runtime_posture: string;
  safety_posture: string;
  signal_pressure_state: string;
  decision_summary: string;
};

export type AutonomousSessionRecommendation = {
  id: number;
  recommendation_type: string;
  target_session: number | null;
  target_tick: number | null;
  target_cadence_decision: number | null;
  rationale: string;
  reason_codes: string[];
  confidence: number;
  blockers: string[];
};

export type AutonomousSessionSummary = {
  active_sessions: number;
  paused_sessions: number;
  stopped_sessions: number;
  session_count: number;
  ticks_executed: number;
  ticks_skipped: number;
  dispatch_count: number;
  closed_outcome_count: number;
  latest_session_id: number | null;
};

export type AutonomousRunnerState = {
  id: number;
  runner_name: string;
  runner_status: 'STOPPED' | 'RUNNING' | 'PAUSED' | 'ERROR';
  last_heartbeat_at: string | null;
  last_successful_run_at: string | null;
  last_error_at: string | null;
  active_session_count: number;
  metadata: Record<string, unknown>;
  updated_at: string;
};

export type AutonomousHeartbeatRun = {
  id: number;
  started_at: string;
  completed_at: string | null;
  runner_status: string;
  considered_session_count: number;
  due_tick_count: number;
  executed_tick_count: number;
  wait_count: number;
  cooldown_skip_count: number;
  blocked_count: number;
  paused_count: number;
  stopped_count: number;
  recommendation_summary: string;
  metadata: Record<string, unknown>;
};

export type AutonomousHeartbeatDecision = {
  id: number;
  linked_heartbeat_run: number;
  linked_session: number;
  linked_latest_tick: number | null;
  decision_type: string;
  decision_status: string;
  due_now: boolean;
  next_due_at: string | null;
  reason_codes: string[];
  decision_summary: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type AutonomousTickDispatchAttempt = {
  id: number;
  linked_session: number;
  linked_heartbeat_decision: number;
  linked_tick: number | null;
  dispatch_status: string;
  automatic: boolean;
  summary: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type AutonomousHeartbeatRecommendation = {
  id: number;
  recommendation_type: string;
  target_session: number | null;
  target_heartbeat_decision: number | null;
  rationale: string;
  reason_codes: string[];
  confidence: number;
  blockers: string[];
  created_at: string;
};

export type AutonomousHeartbeatSummary = {
  runner_state: AutonomousRunnerState;
  latest_run: number | null;
  totals: {
    heartbeat_runs: number;
    decisions: number;
    dispatch_attempts: number;
  };
  runtime_tuning_attention_sync: {
    attempted: boolean;
    success: boolean;
    alert_action: 'CREATED' | 'UPDATED' | 'RESOLVED' | 'NOOP' | 'ERROR' | null;
    human_attention_mode: 'REVIEW_NOW' | 'REVIEW_SOON' | 'MONITOR_ONLY' | 'NO_ACTION' | null;
    next_recommended_scope: string | null;
    material_change_detected?: boolean;
    material_change_fields?: string[];
    update_suppressed?: boolean;
    suppression_reason?: 'NO_MATERIAL_CHANGE' | 'ALERT_NOT_NEEDED' | 'NO_ACTIVE_ALERT' | null;
    active_alert_present?: boolean;
    sync_summary: string;
  };
  live_paper_attention_sync?: LivePaperAttentionAutoSyncStatus | null;
};

export type AutonomousScheduleProfile = {
  id: number;
  slug: string;
  display_name: string;
  is_active: boolean;
  base_interval_seconds: number;
  reduced_interval_seconds: number;
  monitor_only_interval_seconds: number;
  cooldown_extension_seconds: number;
  max_no_action_ticks_before_pause: number;
  max_quiet_ticks_before_wait_long: number;
  max_consecutive_blocked_ticks_before_stop: number;
  enable_auto_pause_for_quiet_markets: boolean;
  enable_auto_stop_for_persistent_blocks: boolean;
  metadata: Record<string, unknown>;
};

export type AutonomousSessionTimingSnapshot = {
  id: number;
  linked_session: number;
  linked_schedule_profile: number | null;
  last_tick_at: string | null;
  next_due_at: string | null;
  active_cooldown_count: number;
  consecutive_no_action_ticks: number;
  consecutive_blocked_ticks: number;
  recent_dispatch_count: number;
  recent_loss_count: number;
  signal_pressure_state: 'HIGH' | 'NORMAL' | 'LOW' | 'QUIET';
  timing_status: 'DUE_NOW' | 'WAIT_SHORT' | 'WAIT_LONG' | 'MONITOR_ONLY_WINDOW' | 'PAUSE_RECOMMENDED' | 'STOP_RECOMMENDED';
  timing_summary: string;
  reason_codes: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type AutonomousStopConditionEvaluation = {
  id: number;
  linked_session: number;
  evaluation_type: string;
  evaluation_status: string;
  evaluation_summary: string;
  reason_codes: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type AutonomousTimingDecision = {
  id: number;
  linked_session: number;
  linked_timing_snapshot: number | null;
  decision_type: string;
  decision_status: string;
  next_due_at: string | null;
  decision_summary: string;
  reason_codes: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type AutonomousTimingRecommendation = {
  id: number;
  recommendation_type: string;
  target_session: number | null;
  target_timing_snapshot: number | null;
  target_timing_decision: number | null;
  rationale: string;
  reason_codes: string[];
  confidence: number;
  blockers: string[];
  created_at: string;
};

export type SessionTimingSummary = {
  summary: {
    sessions_evaluated: number;
    due_now: number;
    waiting_short: number;
    waiting_long: number;
    monitor_only: number;
    pause_recommended: number;
    stop_recommended: number;
  };
  total_profiles: number;
  latest_snapshot_id: number | null;
  latest_decision_id: number | null;
  latest_recommendation_id: number | null;
  extra?: Record<string, unknown>;
};

export type AutonomousProfileSelectionRun = {
  id: number;
  started_at: string;
  completed_at: string | null;
  considered_session_count: number;
  keep_current_profile_count: number;
  switch_recommended_count: number;
  switched_count: number;
  blocked_switch_count: number;
  recommendation_summary: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type AutonomousSessionContextReview = {
  id: number;
  linked_selection_run: number | null;
  linked_session: number;
  linked_current_profile: number | null;
  linked_latest_timing_snapshot: number | null;
  portfolio_pressure_state: 'NORMAL' | 'CAUTION' | 'THROTTLED' | 'BLOCK_NEW_ENTRIES';
  runtime_posture: 'NORMAL' | 'CAUTION' | 'BLOCKED';
  safety_posture: 'NORMAL' | 'CAUTION' | 'HARD_BLOCK';
  signal_pressure_state: 'HIGH' | 'NORMAL' | 'LOW' | 'QUIET';
  recent_loss_state: 'NONE' | 'RECENT_LOSS' | 'REPEATED_LOSS';
  activity_state: 'ACTIVE' | 'LOW_ACTIVITY' | 'REPEATED_NO_ACTION' | 'REPEATED_BLOCKED';
  context_status: 'STABLE' | 'NEEDS_MORE_CONSERVATIVE_PROFILE' | 'NEEDS_MORE_ACTIVE_PROFILE' | 'HOLD_CURRENT' | 'BLOCKED';
  context_summary: string;
  reason_codes: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type AutonomousProfileSwitchDecision = {
  id: number;
  linked_selection_run: number | null;
  linked_session: number;
  linked_context_review: number;
  from_profile: number | null;
  to_profile: number | null;
  decision_type: string;
  decision_status: string;
  decision_summary: string;
  reason_codes: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type AutonomousProfileSwitchRecord = {
  id: number;
  linked_selection_run: number | null;
  linked_session: number;
  linked_switch_decision: number;
  previous_profile: number | null;
  applied_profile: number;
  switch_status: string;
  switch_summary: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type AutonomousProfileRecommendation = {
  id: number;
  recommendation_type: string;
  target_session: number | null;
  target_context_review: number | null;
  target_switch_decision: number | null;
  rationale: string;
  reason_codes: string[];
  confidence: number;
  blockers: string[];
  created_at: string;
};

export type ProfileSelectionSummary = {
  latest_run: number | null;
  summary: {
    sessions_reviewed: number;
    keep_current: number;
    switch_recommended: number;
    switched: number;
    blocked: number;
    manual_review: number;
  };
  totals: {
    runs: number;
    context_reviews: number;
    switch_decisions: number;
    switch_records: number;
  };
  extra?: Record<string, unknown>;
};

export type AutonomousSessionHealthRun = {
  id: number;
  started_at: string;
  completed_at: string | null;
  considered_session_count: number;
  healthy_count: number;
  anomaly_count: number;
  pause_recommended_count: number;
  stop_recommended_count: number;
  resume_recommended_count: number;
  manual_review_count: number;
  intervention_applied_count: number;
  recommendation_summary: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type AutonomousSessionHealthSnapshot = {
  id: number;
  linked_health_run: number | null;
  linked_session: number;
  linked_runner_state: number | null;
  linked_latest_tick: number | null;
  linked_latest_heartbeat_decision: number | null;
  linked_latest_timing_snapshot: number | null;
  session_health_status: 'HEALTHY' | 'CAUTION' | 'DEGRADED' | 'BLOCKED' | 'STALLED';
  consecutive_failed_ticks: number;
  consecutive_blocked_ticks: number;
  consecutive_no_progress_ticks: number;
  has_active_cooldown: boolean;
  runner_session_mismatch: boolean;
  recent_dispatch_count: number;
  recent_outcome_close_count: number;
  recent_loss_count: number;
  incident_pressure_state: 'NONE' | 'CAUTION' | 'HIGH';
  health_summary: string;
  reason_codes: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type AutonomousSessionAnomaly = {
  id: number;
  linked_session: number;
  linked_health_snapshot: number;
  anomaly_type: string;
  anomaly_severity: 'INFO' | 'CAUTION' | 'HIGH' | 'CRITICAL';
  anomaly_summary: string;
  reason_codes: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type AutonomousSessionInterventionDecision = {
  id: number;
  linked_session: number;
  linked_health_snapshot: number;
  decision_type: 'KEEP_RUNNING' | 'PAUSE_SESSION' | 'RESUME_SESSION' | 'STOP_SESSION' | 'REQUIRE_MANUAL_REVIEW' | 'ESCALATE_TO_INCIDENT_REVIEW';
  decision_status: 'PROPOSED' | 'APPLIED' | 'SKIPPED' | 'BLOCKED';
  auto_applicable: boolean;
  decision_summary: string;
  reason_codes: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type AutonomousSessionHealthRecommendation = {
  id: number;
  recommendation_type: string;
  target_session: number | null;
  target_health_snapshot: number | null;
  target_intervention_decision: number | null;
  rationale: string;
  reason_codes: string[];
  confidence: number;
  blockers: string[];
  created_at: string;
};

export type SessionHealthSummary = {
  latest_run_id: number | null;
  summary: {
    sessions_reviewed: number;
    healthy: number;
    anomalies: number;
    pause_recommended: number;
    stop_recommended: number;
    resume_recommended: number;
    manual_review_or_escalation: number;
    interventions_applied: number;
  };
  totals: {
    health_runs: number;
    snapshots: number;
    decisions: number;
    records: number;
    recommendations: number;
  };
  latest_session_id: number | null;
  decision_breakdown: Record<string, number>;
};

export type AutonomousSessionRecoveryRun = {
  id: number;
  started_at: string;
  completed_at: string | null;
  considered_session_count: number;
  ready_to_resume_count: number;
  keep_paused_count: number;
  manual_review_count: number;
  stop_recommended_count: number;
  incident_escalation_count: number;
  recommendation_summary: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type AutonomousSessionRecoverySnapshot = {
  id: number;
  linked_recovery_run: number | null;
  linked_session: number;
  linked_latest_health_snapshot: number | null;
  linked_latest_intervention_decision: number | null;
  linked_latest_intervention_record: number | null;
  linked_latest_timing_snapshot: number | null;
  recovery_status: 'RECOVERED' | 'PARTIALLY_RECOVERED' | 'STILL_BLOCKED' | 'STABILIZING' | 'UNRECOVERABLE';
  safety_block_cleared: boolean;
  runtime_block_cleared: boolean;
  incident_pressure_cleared: boolean;
  portfolio_pressure_state: 'NORMAL' | 'CAUTION' | 'THROTTLED' | 'BLOCK_NEW_ENTRIES';
  cooldown_active: boolean;
  recent_failed_ticks: number;
  recent_blocked_ticks: number;
  recent_successful_ticks: number;
  recovery_summary: string;
  reason_codes: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type AutonomousRecoveryBlocker = {
  id: number;
  linked_session: number;
  linked_recovery_snapshot: number;
  blocker_type: string;
  blocker_severity: 'INFO' | 'CAUTION' | 'HIGH' | 'CRITICAL';
  blocker_summary: string;
  reason_codes: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type AutonomousResumeDecision = {
  id: number;
  linked_session: number;
  linked_recovery_snapshot: number;
  decision_type: 'KEEP_PAUSED' | 'READY_TO_RESUME' | 'RESUME_IN_MONITOR_ONLY_MODE' | 'REQUIRE_MANUAL_RECOVERY_REVIEW' | 'STOP_SESSION_PERMANENTLY' | 'ESCALATE_TO_INCIDENT_REVIEW';
  decision_status: 'PROPOSED' | 'SKIPPED' | 'BLOCKED';
  auto_applicable: boolean;
  decision_summary: string;
  reason_codes: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type AutonomousResumeRecord = {
  id: number;
  linked_session: number;
  linked_resume_decision: number;
  resume_status: 'APPLIED' | 'SKIPPED' | 'BLOCKED' | 'FAILED';
  applied_mode: 'MANUAL_RESUME' | 'AUTO_SAFE_RESUME' | 'MONITOR_ONLY_RESUME';
  resume_summary: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type AutonomousSessionRecoveryRecommendation = {
  id: number;
  recommendation_type: string;
  target_session: number | null;
  target_recovery_snapshot: number | null;
  target_resume_decision: number | null;
  rationale: string;
  reason_codes: string[];
  confidence: number;
  blockers: string[];
  created_at: string;
};

export type SessionRecoverySummary = {
  latest_run_id: number | null;
  summary: {
    sessions_reviewed: number;
    ready_to_resume: number;
    keep_paused: number;
    manual_review: number;
    stop_recommended: number;
    incident_escalation: number;
  };
  totals: {
    recovery_runs: number;
    snapshots: number;
    blockers: number;
    decisions: number;
    records: number;
    recommendations: number;
  };
  decision_breakdown: Record<string, number>;
};

export type AutonomousSessionAdmissionRun = {
  id: number;
  started_at: string;
  completed_at: string | null;
  considered_session_count: number;
  admitted_count: number;
  resume_allowed_count: number;
  parked_count: number;
  deferred_count: number;
  paused_count: number;
  retired_count: number;
  manual_review_count: number;
  recommendation_summary: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type AutonomousGlobalCapacitySnapshot = {
  id: number;
  linked_admission_run: number | null;
  max_active_sessions: number;
  current_running_sessions: number;
  current_paused_sessions: number;
  current_degraded_sessions: number;
  current_blocked_sessions: number;
  active_dispatch_load: number;
  open_position_pressure_state: 'NORMAL' | 'CAUTION' | 'THROTTLED' | 'BLOCK_NEW_ACTIVITY';
  runtime_posture: 'NORMAL' | 'CAUTION' | 'BLOCKED';
  safety_posture: 'NORMAL' | 'CAUTION' | 'HARD_BLOCK';
  incident_pressure_state: 'NONE' | 'CAUTION' | 'HIGH';
  capacity_status: 'AVAILABLE' | 'LIMITED' | 'THROTTLED' | 'BLOCKED';
  snapshot_summary: string;
  reason_codes: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type AutonomousSessionAdmissionReview = {
  id: number;
  linked_admission_run: number | null;
  linked_session: number;
  linked_capacity_snapshot: number;
  linked_latest_health_snapshot: number | null;
  linked_latest_recovery_snapshot: number | null;
  linked_latest_context_review: number | null;
  linked_current_profile: number | null;
  session_priority_state: 'HIGH_VALUE' | 'MEDIUM_VALUE' | 'LOW_VALUE' | 'NO_VALUE';
  session_operability_state: 'READY' | 'RECOVERABLE' | 'CAUTION' | 'BLOCKED' | 'RETIRE_CANDIDATE';
  admission_status: 'ADMIT' | 'RESUME_ALLOWED' | 'PARK' | 'DEFER' | 'PAUSE' | 'RETIRE' | 'MANUAL_REVIEW';
  review_summary: string;
  reason_codes: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type AutonomousSessionAdmissionDecision = {
  id: number;
  linked_session: number;
  linked_admission_review: number;
  decision_type: 'ADMIT_SESSION' | 'ALLOW_RESUME' | 'PARK_SESSION' | 'DEFER_SESSION' | 'PAUSE_SESSION' | 'RETIRE_SESSION' | 'REQUIRE_MANUAL_ADMISSION_REVIEW';
  decision_status: 'PROPOSED' | 'APPLIED' | 'SKIPPED' | 'BLOCKED';
  auto_applicable: boolean;
  decision_summary: string;
  reason_codes: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type AutonomousSessionAdmissionRecommendation = {
  id: number;
  recommendation_type: string;
  target_session: number | null;
  target_admission_review: number | null;
  target_admission_decision: number | null;
  rationale: string;
  reason_codes: string[];
  confidence: number;
  blockers: string[];
  created_at: string;
};

export type SessionAdmissionSummary = {
  latest_run_id: number | null;
  summary: {
    sessions_considered: number;
    admitted: number;
    resume_allowed: number;
    parked: number;
    deferred: number;
    paused: number;
    retired: number;
    manual_review: number;
  };
  latest_capacity_snapshot_id: number | null;
  totals: {
    runs: number;
    capacity_snapshots: number;
    reviews: number;
    decisions: number;
    recommendations: number;
  };
};

export type GovernanceReviewQueueRun = {
  id: number;
  started_at: string;
  completed_at: string | null;
  collected_item_count: number;
  high_priority_count: number;
  blocked_count: number;
  deferred_count: number;
  manual_review_count: number;
  metadata: Record<string, unknown>;
};

export type GovernanceReviewItem = {
  id: number;
  source_module: 'runtime_governor' | 'mission_control' | 'portfolio_governor';
  source_type: 'mode_feedback_apply' | 'mode_stabilization' | 'session_health' | 'session_recovery' | 'session_admission' | 'exposure_coordination' | 'exposure_apply';
  source_object_id: number;
  item_status: 'OPEN' | 'IN_REVIEW' | 'RESOLVED' | 'DISMISSED';
  severity: 'INFO' | 'CAUTION' | 'HIGH' | 'CRITICAL';
  queue_priority: 'P1' | 'P2' | 'P3' | 'P4';
  linked_session: number | null;
  linked_market: number | null;
  title: string;
  summary: string;
  blockers: string[];
  reason_codes: string[];
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type GovernanceReviewRecommendation = {
  id: number;
  linked_review_item: number | null;
  recommendation_type: 'REVIEW_NOW' | 'SAFE_TO_DISMISS' | 'RETRY_LATER' | 'REQUIRE_OPERATOR_CONFIRMATION' | 'ESCALATE_PRIORITY';
  rationale: string;
  confidence: number;
  blockers: string[];
  created_at: string;
};

export type GovernanceReviewResolution = {
  id: number;
  linked_review_item: number;
  resolution_type: 'APPLY_MANUAL_APPROVAL' | 'KEEP_BLOCKED' | 'DISMISS_AS_EXPECTED' | 'REQUIRE_FOLLOWUP' | 'RETRY_SAFE_APPLY';
  resolution_status: 'APPLIED' | 'SKIPPED' | 'BLOCKED' | 'FAILED';
  resolution_summary: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type GovernanceReviewSummary = {
  latest_run: number | null;
  open_count: number;
  resolved_count: number;
  high_priority_count: number;
  blocked_count: number;
  deferred_count: number;
  manual_review_count: number;
  by_source_module: Record<string, number>;
};

export type GovernanceAutoResolutionRun = {
  id: number;
  started_at: string;
  completed_at: string | null;
  considered_item_count: number;
  eligible_count: number;
  applied_count: number;
  skipped_count: number;
  blocked_count: number;
  metadata: Record<string, unknown>;
};

export type GovernanceAutoResolutionDecision = {
  id: number;
  linked_review_item: number;
  linked_auto_resolution_run: number | null;
  decision_type: 'AUTO_DISMISS' | 'AUTO_RETRY_SAFE_APPLY' | 'AUTO_REQUIRE_FOLLOWUP' | 'DO_NOT_AUTO_RESOLVE';
  decision_status: 'PROPOSED' | 'APPLIED' | 'SKIPPED' | 'BLOCKED';
  auto_applicable: boolean;
  decision_summary: string;
  reason_codes: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type GovernanceAutoResolutionRecord = {
  id: number;
  linked_review_item: number;
  linked_auto_resolution_decision: number;
  record_status: 'APPLIED' | 'SKIPPED' | 'BLOCKED' | 'FAILED';
  effect_type: 'DISMISSED' | 'RETRY_SAFE_APPLY_TRIGGERED' | 'FOLLOWUP_MARKED' | 'NO_CHANGE';
  record_summary: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type GovernanceAutoResolutionSummary = {
  latest_run_id: number | null;
  totals: {
    runs: number;
    decisions: number;
    records: number;
  };
  latest_counts: {
    considered: number;
    eligible: number;
    applied: number;
    skipped: number;
    blocked: number;
  };
  decision_breakdown: Record<string, number>;
};

export type GovernanceQueueAgingRun = {
  id: number;
  started_at: string;
  completed_at: string | null;
  considered_item_count: number;
  stale_item_count: number;
  escalated_count: number;
  followup_due_count: number;
  blocked_stale_count: number;
  metadata: Record<string, unknown>;
};

export type GovernanceQueueAgingReview = {
  id: number;
  linked_review_item: number;
  linked_aging_run: number | null;
  age_bucket: 'FRESH' | 'AGING' | 'STALE' | 'OVERDUE';
  aging_status: 'NORMAL' | 'PRIORITY_ESCALATION' | 'FOLLOWUP_DUE' | 'STALE_BLOCKED' | 'MANUAL_REVIEW_OVERDUE';
  review_summary: string;
  reason_codes: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type GovernanceQueueAgingRecommendation = {
  id: number;
  linked_review_item: number;
  linked_aging_review: number | null;
  recommendation_type: 'KEEP_PRIORITY' | 'ESCALATE_TO_P1' | 'ESCALATE_TO_P2' | 'REQUIRE_FOLLOWUP_NOW' | 'ESCALATE_BLOCKED_ITEM' | 'REQUIRE_OPERATOR_REVIEW_NOW';
  rationale: string;
  confidence: number;
  blockers: string[];
  created_at: string;
};

export type GovernanceQueueAgingSummary = {
  latest_run_id: number | null;
  latest_counts: {
    considered: number;
    stale_items: number;
    escalated: number;
    followup_due: number;
    blocked_stale: number;
    overdue: number;
    manual_review_overdue: number;
  };
  totals: {
    runs: number;
    reviews: number;
    recommendations: number;
  };
  status_breakdown: Record<string, number>;
};

export type GovernanceBacklogPressureRun = {
  id: number;
  started_at: string;
  completed_at: string | null;
  considered_item_count: number;
  pressure_state: 'NORMAL' | 'CAUTION' | 'HIGH';
  metadata: Record<string, unknown>;
};

export type GovernanceBacklogPressureSnapshot = {
  id: number;
  linked_backlog_pressure_run: number | null;
  open_item_count: number;
  overdue_count: number;
  overdue_p1_count: number;
  stale_blocked_count: number;
  persistent_stale_blocked_count: number;
  pressure_score: number;
  governance_backlog_pressure_state: 'NORMAL' | 'CAUTION' | 'HIGH';
  snapshot_summary: string;
  reason_codes: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type GovernanceBacklogPressureDecision = {
  id: number;
  linked_backlog_pressure_snapshot: number;
  linked_backlog_pressure_run: number | null;
  decision_type: 'KEEP_NORMAL_PRESSURE' | 'SET_CAUTION_PRESSURE' | 'SET_HIGH_PRESSURE';
  decision_summary: string;
  reason_codes: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type GovernanceBacklogPressureRecommendation = {
  id: number;
  linked_backlog_pressure_decision: number;
  linked_backlog_pressure_snapshot: number | null;
  recommendation_type: 'KEEP_BASELINE' | 'PREFER_REDUCED_CADENCE' | 'LIMIT_NEW_ACTIVITY';
  rationale: string;
  confidence: number;
  blockers: string[];
  created_at: string;
};

export type GovernanceBacklogPressureSummary = {
  latest_run_id: number | null;
  governance_backlog_pressure_state: 'NORMAL' | 'CAUTION' | 'HIGH';
  latest_counts: {
    considered: number;
    open_items: number;
    overdue: number;
    overdue_p1: number;
    stale_blocked: number;
    persistent_stale_blocked: number;
  };
  totals: {
    runs: number;
    snapshots: number;
    decisions: number;
    recommendations: number;
  };
  latest_decision: {
    id: number | null;
    decision_type: string | null;
  };
};

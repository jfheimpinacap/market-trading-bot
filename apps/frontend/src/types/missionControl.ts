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

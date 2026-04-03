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

export type GovernanceBacklogPressureRun = {
  id: number;
  started_at: string;
  completed_at: string | null;
  considered_item_count: number;
  high_priority_item_count: number;
  overdue_item_count: number;
  blocked_stale_count: number;
  followup_due_count: number;
  metadata: Record<string, unknown>;
};

export type GovernanceBacklogPressureSnapshot = {
  id: number;
  linked_pressure_run: number | null;
  open_item_count: number;
  in_review_count: number;
  p1_count: number;
  p2_count: number;
  overdue_count: number;
  stale_blocked_count: number;
  followup_due_count: number;
  pressure_state: 'NORMAL' | 'CAUTION' | 'HIGH' | 'CRITICAL';
  snapshot_summary: string;
  reason_codes: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type GovernanceBacklogPressureDecision = {
  id: number;
  linked_pressure_snapshot: number;
  decision_type: 'KEEP_BACKLOG_PRESSURE_NORMAL' | 'ELEVATE_RUNTIME_CAUTION_SIGNAL' | 'ELEVATE_MONITOR_ONLY_BIAS' | 'REQUIRE_MANUAL_BACKLOG_REVIEW';
  decision_status: 'PROPOSED' | 'APPLIED' | 'SKIPPED' | 'BLOCKED';
  decision_summary: string;
  reason_codes: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type GovernanceBacklogPressureRecommendation = {
  id: number;
  linked_pressure_snapshot: number | null;
  linked_pressure_decision: number | null;
  recommendation_type: 'KEEP_BACKLOG_STABLE' | 'REDUCE_RUNTIME_INTENSITY_FOR_BACKLOG' | 'INCREASE_MANUAL_REVIEW_URGENCY' | 'REQUIRE_BACKLOG_CLEARING';
  rationale: string;
  confidence: number;
  blockers: string[];
  created_at: string;
};

export type GovernanceBacklogPressureSummary = {
  latest_run_id: number | null;
  governance_backlog_pressure_state: 'NORMAL' | 'CAUTION' | 'HIGH' | 'CRITICAL';
  latest_snapshot_id: number | null;
  latest_decision_id: number | null;
  latest_recommendation_id: number | null;
  totals: {
    runs: number;
    snapshots: number;
    decisions: number;
    recommendations: number;
  };
  latest_counts: {
    considered_item_count: number;
    high_priority_item_count: number;
    overdue_item_count: number;
    blocked_stale_count: number;
    followup_due_count: number;
  };
};

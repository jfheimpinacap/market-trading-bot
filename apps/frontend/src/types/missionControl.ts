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

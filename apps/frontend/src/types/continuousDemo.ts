export type ContinuousDemoSessionStatus = 'IDLE' | 'RUNNING' | 'PAUSED' | 'STOPPED' | 'FAILED';
export type ContinuousDemoCycleStatus = 'SUCCESS' | 'PARTIAL' | 'FAILED' | 'SKIPPED';

export type ContinuousDemoSession = {
  id: number;
  session_status: ContinuousDemoSessionStatus;
  started_at: string;
  finished_at: string | null;
  last_cycle_at: string | null;
  total_cycles: number;
  total_auto_executed: number;
  total_pending_approvals: number;
  total_blocked: number;
  total_errors: number;
  summary: string;
  settings_snapshot: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type ContinuousDemoCycleRun = {
  id: number;
  session: number;
  session_status: ContinuousDemoSessionStatus;
  cycle_number: number;
  status: ContinuousDemoCycleStatus;
  started_at: string;
  finished_at: string | null;
  actions_run: Array<Record<string, unknown>>;
  markets_evaluated: number;
  proposals_generated: number;
  auto_executed_count: number;
  approval_required_count: number;
  blocked_count: number;
  summary: string;
  details: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type ContinuousDemoRuntime = {
  id: number;
  runtime_status: ContinuousDemoSessionStatus;
  enabled: boolean;
  kill_switch: boolean;
  stop_requested: boolean;
  pause_requested: boolean;
  cycle_in_progress: boolean;
  last_heartbeat_at: string | null;
  last_error: string;
  active_session: number | null;
  default_settings: Record<string, unknown>;
};

export type ContinuousDemoStatus = {
  runtime: ContinuousDemoRuntime | null;
  active_session: ContinuousDemoSession | null;
  latest_cycle: ContinuousDemoCycleRun | null;
  pending_approvals: number;
};

export type ContinuousDemoControlResponse = {
  stopped?: boolean;
  kill_switch?: boolean;
  session?: ContinuousDemoSession | null;
  detail?: string;
} & Partial<ContinuousDemoSession>;

export type ContinuousDemoSummary = {
  latest_session: ContinuousDemoSession | null;
  latest_cycle: ContinuousDemoCycleRun | null;
  recent_failures: number;
  recent_cycles: number;
};

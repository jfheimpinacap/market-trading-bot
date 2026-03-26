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

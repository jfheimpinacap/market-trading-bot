export type ReplayRunStatus = 'READY' | 'RUNNING' | 'SUCCESS' | 'PARTIAL' | 'FAILED';

export type ReplayRun = {
  id: number;
  status: ReplayRunStatus;
  source_scope: 'real_only' | 'demo_only' | 'mixed';
  provider_scope: string;
  replay_start_at: string;
  replay_end_at: string;
  started_at: string | null;
  finished_at: string | null;
  snapshots_considered: number;
  markets_considered: number;
  proposals_generated: number;
  trades_executed: number;
  approvals_required: number;
  blocked_count: number;
  total_pnl: string;
  ending_equity: string;
  summary: string;
  details: Record<string, unknown>;
  paper_account: number | null;
  created_at: string;
  updated_at: string;
};

export type ReplayStep = {
  id: number;
  replay_run: number;
  step_index: number;
  step_timestamp: string;
  snapshots_used: number;
  markets_considered: number;
  proposals_generated: number;
  trades_executed: number;
  approvals_required: number;
  blocked_count: number;
  estimated_equity: string;
  notes: string;
  details: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type ReplaySummary = {
  latest_run: ReplayRun | null;
  recent_runs: ReplayRun[];
  total_runs: number;
  successful_runs: number;
};

export type RunReplayPayload = {
  provider_scope: string;
  source_scope: 'real_only' | 'demo_only' | 'mixed';
  start_timestamp: string;
  end_timestamp: string;
  market_limit: number;
  active_only: boolean;
  use_allocation: boolean;
  use_learning_adjustments: boolean;
  auto_execute_allowed: boolean;
  treat_approval_required_as_skip: boolean;
  snapshot_sampling_interval?: number;
  stop_on_error: boolean;
};

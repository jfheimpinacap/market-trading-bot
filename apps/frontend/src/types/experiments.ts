export type StrategyProfileType = 'conservative' | 'balanced' | 'aggressive' | 'custom';
export type StrategyMarketScope = 'demo_only' | 'real_only' | 'mixed';
export type ExperimentRunType = 'replay' | 'live_eval' | 'live_session_compare';
export type ExperimentRunStatus = 'READY' | 'RUNNING' | 'SUCCESS' | 'PARTIAL' | 'FAILED';

export type StrategyProfile = {
  id: number;
  name: string;
  slug: string;
  description: string;
  is_active: boolean;
  profile_type: StrategyProfileType;
  market_scope: StrategyMarketScope;
  config: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type ExperimentRun = {
  id: number;
  strategy_profile: StrategyProfile;
  run_type: ExperimentRunType;
  related_replay_run: number | null;
  related_evaluation_run: number | null;
  related_continuous_session: number | null;
  status: ExperimentRunStatus;
  started_at: string | null;
  finished_at: string | null;
  summary: string;
  details: Record<string, unknown>;
  normalized_metrics: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type RunExperimentPayload = {
  strategy_profile_id: number;
  run_type: ExperimentRunType;
  provider_scope?: string;
  start_timestamp?: string;
  end_timestamp?: string;
  related_continuous_session_id?: number;
  active_only?: boolean;
  use_allocation?: boolean;
  stop_on_error?: boolean;
};

export type ExperimentComparison = {
  left_run: { id: number; profile: string; run_type: ExperimentRunType; metrics: Record<string, unknown> };
  right_run: { id: number; profile: string; run_type: ExperimentRunType; metrics: Record<string, unknown> };
  delta: Record<string, string>;
  interpretation: string[];
};

export type ExperimentSummary = {
  latest_run: ExperimentRun | null;
  recent_runs: ExperimentRun[];
  total_runs: number;
  success_runs: number;
};

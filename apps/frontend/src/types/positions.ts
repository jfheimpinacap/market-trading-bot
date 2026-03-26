export type PositionLifecycleAction = 'HOLD' | 'REDUCE' | 'CLOSE' | 'REVIEW_REQUIRED' | 'BLOCK_ADD' | 'EXPIRED';

export type PositionExitPlan = {
  id: number;
  action: PositionLifecycleAction;
  target_quantity: string;
  quantity_delta: string;
  execution_mode: string;
  queue_required: boolean;
  auto_execute_allowed: boolean;
  final_recommended_action: PositionLifecycleAction;
  execution_path: string;
  explanation: string;
  created_at: string;
};

export type PositionLifecycleDecision = {
  id: number;
  run: number;
  market_title?: string;
  market_id?: number;
  status: PositionLifecycleAction;
  decision_confidence: string;
  rationale: string;
  reason_codes: string[];
  position_snapshot: Record<string, unknown>;
  exit_plan?: PositionExitPlan;
  created_at: string;
};

export type PositionLifecycleRun = {
  id: number;
  status: string;
  watched_positions: number;
  decisions_count: number;
  hold_count: number;
  reduce_count: number;
  close_count: number;
  review_required_count: number;
  summary: string;
  created_at: string;
};

export type PositionLifecycleSummary = {
  total_runs: number;
  total_decisions: number;
  status_counts: Array<{ status: PositionLifecycleAction; count: number }>;
  latest_run: PositionLifecycleRun | null;
  profiles: Array<{ slug: string; label: string; description: string }>;
  paper_demo_only: boolean;
  real_execution_enabled: boolean;
};

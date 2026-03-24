export type EvaluationMetricSet = {
  id: number;
  run: number;
  cycles_count: number;
  proposals_generated: number;
  auto_executed_count: number;
  approval_required_count: number;
  blocked_count: number;
  pending_approvals_count: number;
  trades_executed_count: number;
  reviews_generated_count: number;
  favorable_reviews_count: number;
  neutral_reviews_count: number;
  unfavorable_reviews_count: number;
  approval_rate: string;
  block_rate: string;
  auto_execution_rate: string;
  favorable_review_rate: string;
  total_realized_pnl: string;
  total_unrealized_pnl: string;
  total_pnl: string;
  ending_equity: string;
  equity_delta: string;
  safety_events_count: number;
  cooldown_count: number;
  hard_stop_count: number;
  kill_switch_count: number;
  error_count: number;
  proposal_to_execution_ratio: string;
  execution_to_review_ratio: string;
  unfavorable_review_streak: number;
  average_pnl_per_trade: string;
  average_proposal_score: string;
  average_confidence: string;
  percent_real_market_trades: string;
  percent_demo_market_trades: string;
  percent_auto_approved: string;
  percent_manual_approved: string;
  created_at: string;
  updated_at: string;
};

export type EvaluationRun = {
  id: number;
  related_continuous_session: number | null;
  related_semi_auto_run: number | null;
  evaluation_scope: 'session' | 'recent_window' | 'custom';
  market_scope: 'demo_only' | 'real_only' | 'mixed';
  started_at: string;
  finished_at: string | null;
  status: 'READY' | 'IN_PROGRESS' | 'FAILED';
  summary: string;
  guidance: string[];
  metadata: Record<string, unknown>;
  metric_set?: EvaluationMetricSet;
  created_at: string;
  updated_at: string;
};

export type EvaluationSummary = {
  latest_run: EvaluationRun | null;
  recent_runs: EvaluationRun[];
  total_runs: number;
  completed_runs: number;
};

export type EvaluationComparison = {
  left_run_id: number;
  right_run_id: number;
  delta: {
    total_pnl: string;
    equity_delta: string;
    auto_execution_rate: string;
    block_rate: string;
    favorable_review_rate: string;
    safety_events_count: number;
  };
};

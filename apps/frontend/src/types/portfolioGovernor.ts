export type PortfolioThrottleState = 'NORMAL' | 'CAUTION' | 'THROTTLED' | 'BLOCK_NEW_ENTRIES' | 'FORCE_REDUCE' | string;

export type PortfolioExposureSnapshot = {
  id: number;
  total_equity: string;
  available_cash: string;
  total_exposure: string;
  open_positions: number;
  unrealized_pnl: string;
  recent_drawdown_pct: string;
  cash_reserve_ratio: string;
  concentration_market_ratio: string;
  concentration_provider_ratio: string;
  exposure_by_market: Array<{ label: string; exposure: number; ratio: number }>;
  exposure_by_provider: Array<{ label: string; exposure: number; ratio: number }>;
  exposure_by_category: Array<{ label: string; exposure: number; ratio: number }>;
  created_at_snapshot: string;
};

export type PortfolioThrottleDecision = {
  id: number;
  state: PortfolioThrottleState;
  rationale: string;
  reason_codes: string[];
  recommended_max_new_positions: number;
  recommended_max_size_multiplier: string;
  regime_signals: string[];
  metadata: Record<string, unknown>;
  created_at_decision: string;
};

export type PortfolioGovernanceRun = {
  id: number;
  status: string;
  profile_slug: string;
  started_at: string;
  finished_at: string | null;
  summary: string;
  details: Record<string, unknown>;
  exposure_snapshot: PortfolioExposureSnapshot | null;
  throttle_decision: PortfolioThrottleDecision | null;
};

export type PortfolioGovernanceSummary = {
  latest_run: number | null;
  latest_throttle_state: PortfolioThrottleState;
  open_positions: number;
  total_exposure: string;
  market_concentration: string;
  provider_concentration: string;
  drawdown_signal: string;
  profiles: Array<{ slug: string; label: string }>;
  paper_demo_only: boolean;
  real_execution_enabled: boolean;
};

export type SignalDirection = 'BULLISH' | 'BEARISH' | 'NEUTRAL' | string;
export type SignalStatus = 'ACTIVE' | 'MONITOR' | 'EXPIRED' | 'SUPERSEDED' | string;
export type SignalType = 'MOMENTUM' | 'MEAN_REVERSION' | 'EXTREME' | 'OPPORTUNITY' | 'RISK' | 'DORMANT' | string;

export type MockAgent = {
  id: number;
  name: string;
  slug: string;
  description: string;
  role_type: string;
  is_active: boolean;
  notes: string;
  signal_count: number;
  created_at: string;
  updated_at: string;
};

export type SignalRun = {
  id: number;
  run_type: string;
  started_at: string;
  finished_at: string | null;
  status: string;
  markets_evaluated: number;
  signals_created: number;
  notes: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type MarketSignal = {
  id: number;
  market: number;
  market_title: string;
  market_slug: string;
  market_status: string;
  market_provider_slug: string;
  agent: MockAgent | null;
  run: number | null;
  signal_type: SignalType;
  status: SignalStatus;
  direction: SignalDirection;
  score: string;
  confidence: string;
  headline: string;
  thesis: string;
  rationale?: string;
  signal_probability: string | null;
  market_probability_at_signal: string | null;
  edge_estimate: string | null;
  is_actionable: boolean;
  expires_at: string | null;
  metadata?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type SignalSummary = {
  total_signals: number;
  active_signals: number;
  actionable_signals: number;
  bullish_signals: number;
  bearish_signals: number;
  neutral_signals: number;
  active_agents: number;
  markets_with_signals: number;
  latest_signal_at: string | null;
  latest_run: SignalRun | null;
};

export type SignalFilters = {
  market: string;
  agent: string;
  signal_type: string;
  status: string;
  direction: string;
  is_actionable: string;
  ordering: string;
};

export type SignalQueryParams = Partial<SignalFilters>;

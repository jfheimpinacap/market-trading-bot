export type SignalDirection = 'BULLISH' | 'BEARISH' | 'NEUTRAL' | string;
export type SignalStatus = 'ACTIVE' | 'MONITOR' | 'EXPIRED' | 'SUPERSEDED' | string;
export type SignalType = 'MOMENTUM' | 'MEAN_REVERSION' | 'EXTREME' | 'OPPORTUNITY' | 'RISK' | 'DORMANT' | string;

export type OpportunityStatus = 'WATCH' | 'CANDIDATE' | 'PROPOSAL_READY' | 'BLOCKED' | string;
export type SignalProfileSlug = 'conservative_signal' | 'balanced_signal' | 'aggressive_light_signal';

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

export type SignalFusionRun = {
  id: number;
  status: string;
  profile_slug: SignalProfileSlug | string;
  triggered_by: string;
  started_at: string;
  finished_at: string | null;
  markets_evaluated: number;
  signals_created: number;
  proposal_ready_count: number;
  blocked_count: number;
  notes: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type ProposalGateDecision = {
  should_generate_proposal: boolean;
  proposal_priority: number;
  proposal_reason: string;
  blocked_reason: string;
  metadata: Record<string, unknown>;
};

export type OpportunitySignal = {
  id: number;
  run: number;
  rank: number;
  market: number;
  market_title: string;
  market_slug: string;
  market_provider_slug: string;
  provider_slug: string;
  research_score: string;
  triage_score: string;
  narrative_direction: string;
  narrative_confidence: string;
  source_mix: string;
  prediction_system_probability: string | null;
  prediction_market_probability: string | null;
  edge: string;
  prediction_confidence: string;
  risk_level: string;
  adjusted_quantity: string | null;
  runtime_constraints: Record<string, unknown>;
  opportunity_score: string;
  opportunity_status: OpportunityStatus;
  rationale: string;
  metadata: Record<string, unknown>;
  proposal_gate: ProposalGateDecision | null;
  created_at: string;
  updated_at: string;
};

export type SignalBoardSummary = {
  total_opportunities: number;
  watch_count: number;
  candidate_count: number;
  proposal_ready_count: number;
  blocked_count: number;
  latest_run: SignalFusionRun | null;
  paper_demo_only: boolean;
  real_execution_enabled: boolean;
};

export type MarketSignal = {
  id: number;
  market: number;
  market_title: string;
  market_slug: string;
  market_status: string;
  market_provider_slug: string;
  market_source_type?: 'demo' | 'real_read_only' | string;
  execution_mode?: 'paper_demo_only' | string;
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

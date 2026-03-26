export type RiskAssessment = {
  id: number;
  market: number | null;
  market_title?: string;
  proposal: number | null;
  prediction_score: number | null;
  assessment_status: 'READY' | 'SUCCESS' | 'FAILED' | string;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'BLOCKED' | string;
  risk_score: string | null;
  key_risk_factors: Array<Record<string, unknown>>;
  narrative_risk_summary: string;
  liquidity_risk: string;
  volatility_or_momentum_risk: string;
  confidence_risk: string;
  provider_risk: string;
  runtime_risk: string;
  safety_context: Record<string, unknown>;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type RiskSizingDecision = {
  id: number;
  risk_assessment: number;
  base_quantity: string;
  adjusted_quantity: string;
  sizing_mode: 'fixed' | 'heuristic' | 'kelly_like' | 'capped' | string;
  sizing_rationale: string;
  max_exposure_allowed: string | null;
  reserve_cash_considered: string | null;
  confidence_adjustment: string;
  liquidity_adjustment: string;
  safety_adjustment: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type PositionWatchEvent = {
  id: number;
  watch_run: number;
  paper_position: number | null;
  market_title?: string;
  event_type: 'monitor' | 'caution' | 'review_required' | 'exit_consideration' | 'blocked_context' | string;
  severity: 'info' | 'warning' | 'high' | string;
  summary: string;
  rationale: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type PositionWatchRun = {
  id: number;
  status: string;
  watched_positions: number;
  generated_events: number;
  summary: string;
  metadata: Record<string, unknown>;
  events: PositionWatchEvent[];
  created_at: string;
};

export type RiskSummary = {
  total_assessments: number;
  by_level: Array<{ risk_level: string; count: number }>;
  latest_assessment: RiskAssessment | null;
  total_watch_events: number;
  paper_demo_only: boolean;
  real_execution_enabled: boolean;
};

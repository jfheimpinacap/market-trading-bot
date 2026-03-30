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

export type RiskRuntimeRun = {
  id: number;
  started_at: string;
  completed_at: string | null;
  candidate_count: number;
  approved_count: number;
  blocked_count: number;
  reduced_size_count: number;
  watch_required_count: number;
  sent_to_execution_sim_count: number;
  recommendation_summary: Record<string, number>;
  metadata: Record<string, unknown>;
};

export type RiskRuntimeCandidate = {
  id: number;
  runtime_run: number;
  linked_prediction_assessment: number;
  linked_market: number;
  market_title?: string;
  market_provider: string;
  category: string;
  calibrated_probability: string;
  adjusted_edge: string;
  confidence_score: string;
  uncertainty_score: string;
  evidence_quality_score: string;
  precedent_caution_score: string;
  market_liquidity_context: Record<string, unknown>;
  time_to_resolution: number | null;
  predicted_status: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type RiskApprovalDecision = {
  id: number;
  linked_candidate: number;
  linked_prediction_assessment: number;
  market_title?: string;
  approval_status: 'APPROVED' | 'APPROVED_REDUCED' | 'BLOCKED' | 'NEEDS_REVIEW' | string;
  approval_rationale: string;
  reason_codes: string[];
  blockers: string[];
  risk_score: string;
  max_allowed_exposure: string;
  watch_required: boolean;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type RiskSizingPlan = {
  id: number;
  linked_candidate: number;
  linked_approval_decision: number;
  market_title?: string;
  sizing_mode: string;
  raw_size_fraction: string;
  adjusted_size_fraction: string;
  cap_applied: boolean;
  cap_reason_codes: string[];
  paper_notional_size: string;
  sizing_rationale: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type PositionWatchPlan = {
  id: number;
  linked_candidate: number;
  linked_sizing_plan: number;
  market_title?: string;
  watch_status: 'REQUIRED' | 'OPTIONAL' | 'NOT_NEEDED' | string;
  watch_triggers: Record<string, unknown>;
  review_interval_hint: string;
  escalation_path: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type RiskRuntimeRecommendation = {
  id: number;
  runtime_run: number;
  target_candidate: number | null;
  market_title?: string;
  recommendation_type: string;
  rationale: string;
  reason_codes: string[];
  confidence: string;
  blockers: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type RiskRuntimeSummary = {
  latest_run: RiskRuntimeRun | null;
  approval_counts: Record<string, number>;
  recommendation_counts: Record<string, number>;
  paper_demo_only: boolean;
  real_execution_enabled: boolean;
};

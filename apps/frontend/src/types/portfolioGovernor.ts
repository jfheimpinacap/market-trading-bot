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
  latest_exposure_coordination_run?: number | null;
  exposure_coordination_clusters_reviewed?: number;
  exposure_coordination_manual_reviews?: number;
  profiles: Array<{ slug: string; label: string }>;
  paper_demo_only: boolean;
  real_execution_enabled: boolean;
};

export type PortfolioExposureCoordinationRun = {
  id: number;
  started_at: string;
  completed_at: string | null;
  considered_cluster_count: number;
  concentration_alert_count: number;
  conflict_alert_count: number;
  throttle_count: number;
  defer_count: number;
  park_count: number;
  manual_review_count: number;
  recommendation_summary: Record<string, number>;
  metadata: Record<string, unknown>;
};

export type PortfolioExposureClusterSnapshot = {
  id: number;
  cluster_label: string;
  cluster_type: string;
  net_direction: string;
  session_count: number;
  open_position_count: number;
  pending_dispatch_count: number;
  aggregate_notional_pressure: string;
  aggregate_risk_pressure_state: string;
  concentration_status: string;
  cluster_summary: string;
};

export type SessionExposureContribution = {
  id: number;
  linked_session: number;
  linked_cluster_snapshot: number;
  contribution_role: string;
  contribution_direction: string;
  contribution_strength: string;
  contribution_summary: string;
};

export type PortfolioExposureConflictReview = {
  id: number;
  linked_cluster_snapshot: number;
  review_type: string;
  review_severity: string;
  review_summary: string;
};

export type PortfolioExposureDecision = {
  id: number;
  linked_cluster_snapshot: number;
  linked_conflict_review: number | null;
  decision_type: string;
  decision_status: string;
  auto_applicable: boolean;
  decision_summary: string;
};

export type PortfolioExposureRecommendation = {
  id: number;
  recommendation_type: string;
  target_cluster_snapshot: number | null;
  rationale: string;
  blockers: string[];
  confidence: number;
};

export type PortfolioExposureCoordinationSummary = {
  latest_run_id: number | null;
  clusters_reviewed: number;
  concentration_alerts: number;
  conflict_alerts: number;
  throttles: number;
  defers: number;
  parks: number;
  manual_reviews: number;
  recommendation_summary?: Record<string, number>;
  paper_demo_only: boolean;
  real_execution_enabled: boolean;
};

export type PortfolioExposureApplyRun = {
  id: number;
  started_at: string;
  completed_at: string | null;
  considered_decision_count: number;
  applied_count: number;
  skipped_count: number;
  blocked_count: number;
  deferred_dispatch_apply_count: number;
  parked_session_apply_count: number;
  paused_cluster_apply_count: number;
  recommendation_summary: Record<string, number>;
};

export type PortfolioExposureApplyTarget = {
  id: number;
  linked_exposure_decision: number;
  target_type: string;
  linked_session: number | null;
  linked_dispatch_record: number | null;
  linked_cluster_snapshot: number | null;
  target_status: string;
  target_summary: string;
};

export type PortfolioExposureApplyDecision = {
  id: number;
  linked_exposure_decision: number;
  apply_type: string;
  apply_status: string;
  auto_applicable: boolean;
  apply_summary: string;
};

export type PortfolioExposureApplyRecord = {
  id: number;
  linked_apply_decision: number;
  record_status: string;
  effect_type: string;
  record_summary: string;
};

export type PortfolioExposureApplyRecommendation = {
  id: number;
  recommendation_type: string;
  target_exposure_decision: number | null;
  target_apply_decision: number | null;
  rationale: string;
  blockers: string[];
  confidence: number;
};

export type PortfolioExposureApplySummary = {
  latest_run_id: number | null;
  decisions_considered: number;
  applied: number;
  skipped: number;
  blocked: number;
  deferred_dispatches: number;
  parked_sessions: number;
  paused_clusters: number;
  recommendation_summary?: Record<string, number>;
};

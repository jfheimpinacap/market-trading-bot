export type PromotionRecommendationCode =
  | 'KEEP_CURRENT_CHAMPION'
  | 'PROMOTE_CHALLENGER'
  | 'EXTEND_SHADOW_TEST'
  | 'REVERT_TO_CONSERVATIVE_STACK'
  | 'MANUAL_REVIEW_REQUIRED';

export type PromotionDecisionLog = {
  id: number;
  review_run: number;
  event_type: string;
  actor: string;
  notes: string;
  payload: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type StackEvidenceSnapshot = {
  id: number;
  champion_binding: { id: number; name: string; execution_profile: string };
  challenger_binding: { id: number; name: string; execution_profile: string } | null;
  champion_challenger_summary: Record<string, unknown>;
  execution_aware_metrics: Record<string, number | string>;
  readiness_summary: Record<string, unknown>;
  profile_governance_context: Record<string, unknown>;
  portfolio_governor_context: Record<string, unknown>;
  model_governance_summary: Record<string, unknown>;
  precedent_warnings: Array<Record<string, unknown>>;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type PromotionReviewRun = {
  id: number;
  status: 'COMPLETED' | 'FAILED';
  decision_mode: 'RECOMMENDATION_ONLY' | 'MANUAL_APPLY';
  readiness_status: string;
  evidence_snapshot: StackEvidenceSnapshot;
  recommendation_code: PromotionRecommendationCode;
  confidence: string;
  rationale: string;
  reason_codes: string[];
  blocking_constraints: string[];
  evidence_summary: Record<string, unknown>;
  summary: string;
  metadata: Record<string, unknown>;
  decision_logs: PromotionDecisionLog[];
  created_at: string;
  updated_at: string;
};

export type PromotionSummary = {
  latest_run: PromotionReviewRun | null;
  total_runs: number;
  recommendation_counts: Record<string, number>;
  is_recommendation_stale: boolean;
};

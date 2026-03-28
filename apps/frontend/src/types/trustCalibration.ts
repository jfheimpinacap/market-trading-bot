export type TrustCalibrationRunStatus = 'READY' | 'IN_PROGRESS' | 'FAILED';

export type TrustCalibrationRecommendationType =
  | 'PROMOTE_TO_SAFE_AUTOMATION'
  | 'KEEP_APPROVAL_REQUIRED'
  | 'DOWNGRADE_TO_MANUAL_ONLY'
  | 'BLOCK_AUTOMATION_FOR_ACTION'
  | 'REQUIRE_MORE_DATA'
  | 'REVIEW_RULE_CONDITIONS';

export type TrustCalibrationRun = {
  id: number;
  started_at: string;
  finished_at: string | null;
  status: TrustCalibrationRunStatus;
  window_days: number;
  source_type: string;
  runbook_template_slug: string;
  profile_slug: string;
  include_degraded: boolean;
  summary: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type AutomationFeedbackSnapshot = {
  id: number;
  run: number;
  action_type: string;
  source_type: string;
  runbook_template_slug: string;
  profile_slug: string;
  current_trust_tier: string;
  approvals_granted: number;
  approvals_rejected: number;
  approvals_expired: number;
  approvals_escalated: number;
  auto_actions_executed: number;
  auto_actions_failed: number;
  blocked_decisions: number;
  retry_count: number;
  operator_overrides: number;
  incidents_after_auto: number;
  metrics: Record<string, string | number>;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type TrustCalibrationRecommendation = {
  id: number;
  run: number;
  snapshot: number;
  recommendation_type: TrustCalibrationRecommendationType;
  action_type: string;
  current_trust_tier: string;
  recommended_trust_tier: string;
  confidence: string;
  rationale: string;
  reason_codes: string[];
  supporting_metrics: Record<string, string | number>;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type TrustCalibrationSummary = {
  latest_run: number | null;
  actions_analyzed: number;
  avg_approval_friction: string;
  recommendations_count: number;
  recommendation_breakdown: Record<string, number>;
  top_auto_success_domains: Array<{ action_type: string; current_trust_tier: string; metrics: Record<string, string | number> }>;
  top_caution_domains: Array<{ action_type: string; current_trust_tier: string; metrics: Record<string, string | number> }>;
};

export type RunTrustCalibrationResponse = {
  run: TrustCalibrationRun;
  feedback_count: number;
  recommendation_count: number;
  candidates: Array<{
    recommendation_id: number;
    action_type: string;
    current_trust_tier: string;
    recommended_trust_tier: string;
    recommendation_type: string;
    reason_codes: string[];
    confidence: string;
    apply_mode: 'MANUAL_APPROVAL_REQUIRED';
  }>;
};

export type LaunchReadinessStatus = 'READY_TO_START' | 'CAUTION' | 'WAITING' | 'BLOCKED';
export type LaunchAuthorizationStatus = 'PENDING_REVIEW' | 'AUTHORIZED' | 'HOLD' | 'BLOCKED' | 'EXPIRED';
export type LaunchRecommendationType =
  | 'START_NOW'
  | 'AUTHORIZE_START'
  | 'HOLD_START'
  | 'WAIT_FOR_WINDOW'
  | 'REQUIRE_APPROVAL_TO_START'
  | 'BLOCK_START'
  | 'REORDER_START_PRIORITY';

export type LaunchCandidate = {
  id: number;
  campaign: number;
  campaign_title?: string;
  status: string;
  priority_score: number;
  readiness_score: number;
  blocked_reasons: string[];
};

export type LaunchReadinessSnapshot = {
  id: number;
  campaign: number;
  campaign_title?: string;
  admission_status: string;
  program_posture: string;
  active_window_status: string;
  unresolved_checkpoints_count: number;
  unresolved_approvals_count: number;
  dependency_blocked: boolean;
  domain_conflict: boolean;
  incident_impact: number;
  degraded_impact: number;
  rollout_observation_impact: number;
  readiness_score: number;
  readiness_status: LaunchReadinessStatus;
  blockers: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type LaunchRecommendation = {
  id: number;
  recommendation_type: LaunchRecommendationType;
  target_campaign: number | null;
  target_campaign_title?: string;
  rationale: string;
  reason_codes: string[];
  confidence: string;
  blockers: string[];
  impacted_domains: string[];
  created_at: string;
};

export type LaunchAuthorization = {
  id: number;
  campaign: number;
  campaign_title?: string;
  authorization_status: LaunchAuthorizationStatus;
  authorization_type: string;
  rationale: string;
  reason_codes: string[];
  requires_approval: boolean;
  approved_request: number | null;
  expires_at: string | null;
  created_at: string;
};

export type LaunchSummary = {
  latest_run_id: number | null;
  program_posture: string | null;
  active_window_id: number | null;
  candidate_count: number;
  ready_count: number;
  waiting_count: number;
  blocked_count: number;
  approval_required_count: number;
  latest_recommendation_type: LaunchRecommendationType | null;
  latest_authorization_status: LaunchAuthorizationStatus | null;
};

export type LaunchRunResponse = {
  run: { id: number };
  readiness: LaunchReadinessSnapshot[];
  recommendations: LaunchRecommendation[];
  candidates: LaunchCandidate[];
};

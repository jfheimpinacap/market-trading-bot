export type DispatchReadinessStatus = 'READY_TO_DISPATCH' | 'REVALIDATE_REQUIRED' | 'WAITING' | 'BLOCKED' | 'EXPIRED';
export type ActivationStatus = 'PENDING' | 'DISPATCHING' | 'STARTED' | 'BLOCKED' | 'FAILED' | 'CANCELLED' | 'EXPIRED';
export type ActivationRecommendationType =
  | 'DISPATCH_NOW'
  | 'REVALIDATE_BEFORE_DISPATCH'
  | 'HOLD_DISPATCH'
  | 'BLOCK_DISPATCH'
  | 'WAIT_FOR_WINDOW'
  | 'EXPIRE_AUTHORIZATION'
  | 'REORDER_DISPATCH_PRIORITY';

export type ActivationCandidate = {
  campaign: number;
  campaign_title: string;
  campaign_status: string;
  launch_authorization: number | null;
  authorization_status: string;
  expires_at: string | null;
  current_program_posture: string;
  active_window: number | null;
  active_window_name: string | null;
  domain_conflict: boolean;
  incident_impact: number;
  degraded_impact: number;
  rollout_pressure: number;
  dispatch_readiness_status: DispatchReadinessStatus;
  blockers: string[];
  metadata: Record<string, unknown>;
};

export type CampaignActivation = {
  id: number;
  campaign: number;
  campaign_title?: string;
  launch_authorization: number | null;
  activation_status: ActivationStatus;
  trigger_source: 'manual_ui' | 'manual_api' | 'approval_resume';
  dispatch_rationale: string;
  reason_codes: string[];
  blockers: string[];
  started_campaign_state: string;
  failure_message: string;
  activated_by: string;
  activated_at: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type ActivationRecommendation = {
  id: number;
  recommendation_type: ActivationRecommendationType;
  target_campaign: number | null;
  target_campaign_title?: string;
  rationale: string;
  reason_codes: string[];
  confidence: string;
  blockers: string[];
  impacted_domains: string[];
  created_at: string;
};

export type ActivationRunResponse = {
  run: { id: number };
  candidates: ActivationCandidate[];
  recommendations: ActivationRecommendation[];
};

export type ActivationSummary = {
  latest_run_id: number | null;
  current_program_posture: string | null;
  active_window_id: number | null;
  active_window_name: string | null;
  candidate_count: number;
  ready_count: number;
  blocked_count: number;
  expired_count: number;
  dispatch_started_count: number;
  failed_count: number;
  recent_activations: number;
};

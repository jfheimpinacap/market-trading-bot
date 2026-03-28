export type ProgramConcurrencyPosture = 'NORMAL' | 'CONSTRAINED' | 'HIGH_RISK' | 'FROZEN';
export type CampaignHealthStatus = 'HEALTHY' | 'CAUTION' | 'BLOCKED' | 'AT_RISK';
export type ProgramRecommendationType =
  | 'CONTINUE_CAMPAIGN'
  | 'PAUSE_CAMPAIGN'
  | 'REORDER_QUEUE'
  | 'ABORT_CAMPAIGN'
  | 'HOLD_NEW_CAMPAIGNS'
  | 'SAFE_TO_START_NEXT'
  | 'WAIT_FOR_STABILIZATION';

export type AutonomyProgramStateRecord = {
  id: number;
  active_campaigns_count: number;
  blocked_campaigns_count: number;
  waiting_approval_count: number;
  observing_campaigns_count: number;
  degraded_domains_count: number;
  locked_domains: string[];
  concurrency_posture: ProgramConcurrencyPosture;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type AutonomyProgramStateResponse = {
  state: AutonomyProgramStateRecord;
  conflicts: Array<{ rule_type: string; reason_code: string; details: Record<string, unknown> }>;
  max_active_campaigns: number;
  critical_incident_active: boolean;
};

export type CampaignConcurrencyRule = {
  id: number;
  rule_type: string;
  scope: string;
  config: Record<string, unknown>;
  rationale: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type CampaignHealthSnapshot = {
  id: number;
  campaign: number;
  campaign_title?: string;
  active_wave: number;
  domain_count: number;
  blocked_checkpoints: number;
  open_approvals: number;
  rollout_warnings: number;
  incident_impact: number;
  degraded_impact: number;
  health_score: number;
  health_status: CampaignHealthStatus;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type ProgramRecommendation = {
  id: number;
  recommendation_type: ProgramRecommendationType;
  target_campaign: number | null;
  target_campaign_title?: string;
  rationale: string;
  reason_codes: string[];
  confidence: string;
  impacted_domains: string[];
  blockers: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type AutonomyProgramSummary = {
  program_state_id: number;
  concurrency_posture: ProgramConcurrencyPosture;
  active_campaigns_count: number;
  blocked_campaigns_count: number;
  waiting_approval_count: number;
  observing_campaigns_count: number;
  degraded_domains_count: number;
  locked_domains: string[];
  latest_recommendation_type: ProgramRecommendationType | null;
  latest_recommendation_target: number | null;
  latest_health_status: CampaignHealthStatus | null;
  latest_health_campaign_id: number | null;
};

export type AutonomyProgramRunReviewResponse = {
  state: AutonomyProgramStateRecord;
  health_snapshots: CampaignHealthSnapshot[];
  recommendations: ProgramRecommendation[];
  pause_gates_applied: number;
  conflicts: Array<{ rule_type: string; reason_code: string; details: Record<string, unknown> }>;
};

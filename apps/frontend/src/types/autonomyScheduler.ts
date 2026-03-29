export type CampaignAdmissionStatus = 'PENDING' | 'READY' | 'DEFERRED' | 'BLOCKED' | 'ADMITTED' | 'EXPIRED';
export type ChangeWindowStatus = 'OPEN' | 'UPCOMING' | 'CLOSED' | 'FROZEN';
export type AdmissionRecommendationType =
  | 'ADMIT_CAMPAIGN'
  | 'DEFER_CAMPAIGN'
  | 'HOLD_QUEUE'
  | 'WAIT_FOR_WINDOW'
  | 'REORDER_ADMISSION_QUEUE'
  | 'SAFE_TO_ADMIT_NEXT'
  | 'BLOCK_ADMISSION'
  | 'REQUIRE_APPROVAL_TO_ADMIT';

export type CampaignAdmission = {
  id: number;
  campaign: number;
  campaign_title?: string;
  status: CampaignAdmissionStatus;
  source_type: 'roadmap_plan' | 'scenario_run' | 'manual';
  priority_score: number;
  readiness_score: number;
  blocked_reasons: string[];
  requested_window: number | null;
  admitted_at: string | null;
  deferred_until: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type ChangeWindow = {
  id: number;
  name: string;
  status: ChangeWindowStatus;
  window_type: 'normal_change' | 'cautious_change' | 'observation_only' | 'freeze_window';
  starts_at: string | null;
  ends_at: string | null;
  max_new_admissions: number;
  allowed_postures: string[];
  blocked_domains: string[];
  rationale: string;
  metadata: Record<string, unknown>;
};

export type SchedulerRun = {
  id: number;
  queue_counts: Record<string, number>;
  ready_campaigns: number[];
  blocked_campaigns: number[];
  deferred_campaigns: number[];
  current_program_posture: string;
  active_window: number | null;
  max_admissible_starts: number;
  recommendations_summary: Record<string, unknown>;
  created_at: string;
};

export type AdmissionRecommendation = {
  id: number;
  scheduler_run: number | null;
  recommendation_type: AdmissionRecommendationType;
  target_campaign: number | null;
  target_campaign_title?: string;
  rationale: string;
  reason_codes: string[];
  confidence: string;
  blockers: string[];
  impacted_domains: string[];
  recommended_window: number | null;
  created_at: string;
};

export type SchedulerRunPlanResponse = {
  run: SchedulerRun;
  recommendations: AdmissionRecommendation[];
  queue: CampaignAdmission[];
  active_window: ChangeWindow | null;
};

export type AutonomySchedulerSummary = {
  latest_run_id: number | null;
  current_program_posture: string | null;
  active_window_id: number | null;
  max_admissible_starts: number;
  queue_counts: Record<string, number>;
  latest_recommendation_type: AdmissionRecommendationType | null;
  latest_recommendation_campaign_id: number | null;
};

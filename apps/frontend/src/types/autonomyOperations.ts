export type CampaignRuntimeStatus = 'ON_TRACK' | 'CAUTION' | 'STALLED' | 'BLOCKED' | 'WAITING_APPROVAL' | 'OBSERVING';
export type CampaignAttentionSeverity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type CampaignAttentionSignalStatus = 'OPEN' | 'ACKNOWLEDGED' | 'RESOLVED';

export type CampaignRuntimeSnapshot = {
  id: number;
  campaign: number;
  campaign_title?: string;
  campaign_status: string;
  current_wave: number | null;
  current_step: number | null;
  current_step_order?: number | null;
  current_checkpoint: number | null;
  current_checkpoint_summary?: string | null;
  started_at: string | null;
  last_progress_at: string | null;
  stalled_duration_seconds: number | null;
  open_checkpoints_count: number;
  pending_approvals_count: number;
  blocked_steps_count: number;
  incident_impact: number;
  degraded_impact: number;
  rollout_observation_impact: number;
  progress_score: string;
  runtime_status: CampaignRuntimeStatus;
  blockers: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type CampaignAttentionSignal = {
  id: number;
  campaign: number;
  campaign_title?: string;
  severity: CampaignAttentionSeverity;
  signal_type: string;
  status: CampaignAttentionSignalStatus;
  rationale: string;
  reason_codes: string[];
  blockers: string[];
  linked_trace: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type OperationsRecommendation = {
  id: number;
  recommendation_type: string;
  target_campaign: number | null;
  target_campaign_title?: string | null;
  rationale: string;
  reason_codes: string[];
  confidence: string;
  blockers: string[];
  impacted_domains: string[];
  created_at: string;
};

export type AutonomyOperationsSummary = {
  latest_run_id: number | null;
  active_campaign_count: number;
  on_track_count: number;
  caution_count: number;
  stalled_count: number;
  blocked_count: number;
  waiting_approval_count: number;
  observing_count: number;
  attention_signal_count: number;
  open_attention_signal_count: number;
  recommendation_summary: Record<string, number>;
};

export type RunAutonomyOperationsMonitorResponse = {
  run: number;
  runtime_count: number;
  signal_count: number;
  recommendation_count: number;
};

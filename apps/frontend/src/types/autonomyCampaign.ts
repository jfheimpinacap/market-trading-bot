export type AutonomyCampaignSourceType = 'roadmap_plan' | 'scenario_run' | 'manual_bundle';
export type AutonomyCampaignStatus = 'DRAFT' | 'READY' | 'RUNNING' | 'PAUSED' | 'BLOCKED' | 'COMPLETED' | 'ABORTED' | 'FAILED';
export type AutonomyCampaignStepStatus = 'PENDING' | 'READY' | 'RUNNING' | 'WAITING_APPROVAL' | 'OBSERVING' | 'DONE' | 'FAILED' | 'SKIPPED' | 'ABORTED';

export type AutonomyCampaignStep = {
  id: number;
  campaign: number;
  step_order: number;
  wave: number;
  domain: number | null;
  domain_slug?: string;
  action_type: 'APPLY_TRANSITION' | 'START_ROLLOUT' | 'EVALUATE_ROLLOUT';
  status: AutonomyCampaignStepStatus;
  rationale: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type AutonomyCampaignCheckpoint = {
  id: number;
  campaign: number;
  step: number;
  checkpoint_type: string;
  status: 'OPEN' | 'SATISFIED' | 'REJECTED' | 'EXPIRED';
  summary: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type AutonomyCampaign = {
  id: number;
  source_type: AutonomyCampaignSourceType;
  source_object_id: string;
  title: string;
  summary: string;
  status: AutonomyCampaignStatus;
  current_wave: number;
  total_steps: number;
  completed_steps: number;
  blocked_steps: number;
  metadata: Record<string, unknown>;
  steps: AutonomyCampaignStep[];
  checkpoints: AutonomyCampaignCheckpoint[];
  created_at: string;
  updated_at: string;
};

export type AutonomyCampaignSummary = {
  total_campaigns: number;
  active_campaigns: number;
  latest_campaign_id: number | null;
  latest_status: AutonomyCampaignStatus | null;
  latest_source_type: AutonomyCampaignSourceType | null;
  status_breakdown: Record<string, number>;
};

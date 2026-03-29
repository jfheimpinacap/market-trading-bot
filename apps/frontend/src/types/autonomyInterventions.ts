export type InterventionRequestStatus = 'OPEN' | 'APPROVAL_REQUIRED' | 'READY' | 'EXECUTED' | 'REJECTED' | 'BLOCKED' | 'EXPIRED';

export type CampaignInterventionRequest = {
  id: number;
  campaign: number;
  campaign_title?: string;
  source_type: string;
  requested_action: string;
  request_status: InterventionRequestStatus;
  severity: string;
  rationale: string;
  reason_codes: string[];
  blockers: string[];
  approval_request: number | null;
  requested_by: string;
  created_at: string;
  updated_at: string;
};

export type CampaignInterventionAction = {
  id: number;
  campaign: number;
  campaign_title?: string;
  intervention_request: number | null;
  action_type: string;
  action_status: string;
  executed_by: string;
  executed_at: string | null;
  failure_message: string;
  result_summary: string;
  blockers: string[];
  created_at: string;
};

export type AutonomyInterventionSummary = {
  latest_run_id: number | null;
  active_campaign_count: number;
  open_request_count: number;
  approval_required_count: number;
  ready_request_count: number;
  blocked_request_count: number;
  executed_recent_count: number;
  campaigns_needing_intervention: number;
  recommendation_summary: Record<string, number>;
};

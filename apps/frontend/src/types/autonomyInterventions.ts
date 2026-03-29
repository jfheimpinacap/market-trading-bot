export type InterventionRequestStatus = 'OPEN' | 'APPROVAL_REQUIRED' | 'READY' | 'EXECUTED' | 'REJECTED' | 'BLOCKED' | 'EXPIRED';

export type InterventionActionType = 'pause' | 'resume' | 'escalate' | 'abort_review' | 'continue_clearance';

export type InterventionActionStatus = 'PENDING' | 'EXECUTING' | 'EXECUTED' | 'BLOCKED' | 'FAILED' | 'CANCELLED';

export type CampaignInterventionRequest = {
  id: number;
  campaign: number;
  campaign_title?: string;
  source_type: 'operations_recommendation' | 'attention_signal' | 'manual' | 'incident_response';
  requested_action: 'PAUSE_CAMPAIGN' | 'RESUME_CAMPAIGN' | 'ESCALATE_TO_APPROVAL' | 'REVIEW_FOR_ABORT' | 'CLEAR_TO_CONTINUE';
  request_status: InterventionRequestStatus;
  severity: string;
  rationale: string;
  reason_codes: string[];
  blockers: string[];
  linked_signal: number | null;
  linked_recommendation: number | null;
  approval_request: number | null;
  requested_by: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type CampaignInterventionAction = {
  id: number;
  campaign: number;
  campaign_title?: string;
  intervention_request: number | null;
  action_type: InterventionActionType;
  action_status: InterventionActionStatus;
  executed_by: string;
  executed_at: string | null;
  failure_message: string;
  result_summary: string;
  reason_codes: string[];
  blockers: string[];
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type AutonomyInterventionSummary = {
  active_campaign_count: number;
  open_request_count: number;
  approval_required_count: number;
  ready_request_count: number;
  blocked_request_count: number;
  executed_recent_count: number;
  recommendation_summary: Record<string, number>;
  campaigns_needing_intervention: number;
  open_attention_signal_count: number;
};

export type RunAutonomyInterventionReviewResponse = {
  run_id: number;
  created_request_count: number;
  created_request_ids: number[];
};

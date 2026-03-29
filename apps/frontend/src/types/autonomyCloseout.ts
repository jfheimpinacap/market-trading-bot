export type CloseoutStatus = 'PENDING_REVIEW' | 'READY' | 'APPROVAL_REQUIRED' | 'COMPLETED' | 'BLOCKED';

export type AutonomyCloseoutCandidate = {
  campaign: number;
  campaign_title: string;
  disposition_type: string;
  disposition_status: string;
  final_campaign_status: string;
  ready_for_closeout: boolean;
  requires_postmortem: boolean;
  requires_memory_index: boolean;
  requires_roadmap_feedback: boolean;
  unresolved_blockers: string[];
  unresolved_approvals_count: number;
  incident_history_level: 'LOW' | 'MEDIUM' | 'HIGH';
  intervention_count: number;
  metadata: Record<string, unknown>;
};

export type CampaignCloseoutReport = {
  id: number;
  campaign: number;
  campaign_title?: string;
  disposition_type: string;
  closeout_status: CloseoutStatus;
  executive_summary: string;
  lifecycle_summary: Record<string, unknown>;
  major_blockers: string[];
  incident_summary: Record<string, unknown>;
  intervention_summary: Record<string, unknown>;
  recovery_summary: Record<string, unknown>;
  final_outcome_summary: string;
  requires_postmortem: boolean;
  requires_memory_index: boolean;
  requires_roadmap_feedback: boolean;
  linked_postmortem_request: string;
  linked_memory_document: number | null;
  linked_feedback_artifact: string;
  closed_out_by: string;
  closed_out_at: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type CloseoutFinding = {
  id: number;
  closeout_report: number;
  campaign: number;
  campaign_title?: string;
  finding_type: string;
  severity_or_weight: string;
  summary: string;
  reason_codes: string[];
  recommended_followup: string;
  created_at: string;
};

export type CloseoutRecommendation = {
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

export type CloseoutSummary = {
  latest_run_id: number | null;
  candidate_count: number;
  ready_count: number;
  blocked_count: number;
  requires_postmortem_count: number;
  requires_memory_index_count: number;
  requires_roadmap_feedback_count: number;
  completed_closeout_count: number;
  recommendation_summary: Record<string, number>;
};

export type RunCloseoutReviewResponse = {
  run: number;
  report_count: number;
  recommendation_count: number;
};

export type DispositionReadiness = 'READY_TO_CLOSE' | 'READY_TO_ABORT' | 'READY_TO_RETIRE' | 'REQUIRE_MORE_REVIEW' | 'KEEP_OPEN';

export type CampaignDispositionCandidate = {
  campaign: number;
  campaign_title: string;
  campaign_status: string;
  recovery_status: string | null;
  last_intervention_outcome: string | null;
  last_runtime_status: string | null;
  disposition_readiness: DispositionReadiness;
  open_blockers: string[];
  pending_approvals_count: number;
  unresolved_checkpoints_count: number;
  unresolved_incident_pressure: number;
  closure_risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
  recommended_disposition: string;
  metadata: { reason_codes: string[]; requires_approval: boolean };
};

export type CampaignDisposition = {
  id: number;
  campaign: number;
  campaign_title?: string;
  disposition_type: string;
  disposition_status: string;
  rationale: string;
  reason_codes: string[];
  blockers: string[];
  requires_approval: boolean;
  linked_approval_request: number | null;
  applied_by: string;
  applied_at: string | null;
  campaign_state_before: string;
  campaign_state_after: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type DispositionRecommendation = {
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

export type DispositionSummary = {
  latest_run_id: number | null;
  candidate_count: number;
  ready_to_close_count: number;
  ready_to_abort_count: number;
  ready_to_retire_count: number;
  require_more_review_count: number;
  keep_open_count: number;
  approval_required_count: number;
  recommendation_summary: Record<string, number>;
};

export type RunDispositionReviewResponse = {
  run: number;
  disposition_count: number;
  recommendation_count: number;
};

export type AutonomyPlanningReviewCandidate = {
  planning_proposal: number;
  backlog_item: number | null;
  advisory_artifact: number | null;
  insight: number | null;
  campaign: number | null;
  campaign_title: string | null;
  proposal_type: string;
  proposal_status: string;
  target_scope: string;
  downstream_status: string;
  ready_for_resolution: boolean;
  blockers: string[];
  metadata: Record<string, unknown>;
};

export type PlanningProposalResolution = {
  id: number;
  planning_proposal: number;
  backlog_item: number | null;
  advisory_artifact: number | null;
  insight: number | null;
  campaign: number | null;
  campaign_title?: string | null;
  resolution_status: string;
  resolution_type: string;
  rationale: string;
  reason_codes: string[];
  blockers: string[];
  resolved_by: string;
  resolved_at: string | null;
  linked_target_artifact: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type PlanningReviewRecommendation = {
  id: number;
  planning_proposal: number | null;
  backlog_item: number | null;
  recommendation_type: string;
  rationale: string;
  reason_codes: string[];
  confidence: string;
  blockers: string[];
  created_at: string;
};

export type AutonomyPlanningReviewSummary = {
  latest_run_id: number | null;
  planning_proposals_emitted_count: number;
  candidate_count: number;
  pending_count: number;
  acknowledged_count: number;
  accepted_count: number;
  deferred_count: number;
  rejected_count: number;
  blocked_count: number;
  closed_count: number;
  recommendation_summary: Record<string, number>;
};

export type RunAutonomyPlanningReviewResponse = {
  run: number;
  candidate_count: number;
  resolution_count: number;
  recommendation_count: number;
};

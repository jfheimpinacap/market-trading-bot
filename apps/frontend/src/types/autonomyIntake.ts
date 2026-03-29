export type AutonomyIntakeCandidate = {
  backlog_item: number;
  advisory_artifact: number;
  insight: number;
  campaign: number | null;
  campaign_title: string | null;
  backlog_type: string;
  target_scope: string;
  priority_level: string;
  ready_for_intake: boolean;
  existing_proposal: number | null;
  blockers: string[];
  metadata: Record<string, unknown>;
};

export type PlanningProposal = {
  id: number;
  backlog_item: number;
  advisory_artifact: number | null;
  insight: number | null;
  campaign: number | null;
  campaign_title?: string | null;
  proposal_type: string;
  proposal_status: string;
  target_scope: string;
  priority_level: string;
  summary: string;
  rationale: string;
  reason_codes: string[];
  blockers: string[];
  emitted_by: string;
  emitted_at: string | null;
  linked_target_artifact: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type IntakeRecommendation = {
  id: number;
  backlog_item: number | null;
  proposal: number | null;
  proposal_type: string;
  recommendation_type: string;
  rationale: string;
  reason_codes: string[];
  confidence: string;
  blockers: string[];
  created_at: string;
};

export type AutonomyIntakeSummary = {
  latest_run_id: number | null;
  candidate_count: number;
  ready_count: number;
  blocked_count: number;
  emitted_count: number;
  duplicate_skipped_count: number;
  roadmap_proposal_count: number;
  scenario_proposal_count: number;
  program_proposal_count: number;
  manager_proposal_count: number;
  recommendation_summary: Record<string, number>;
  total_proposals: number;
  pending_review: number;
  ready: number;
  emitted: number;
  acknowledged: number;
};

export type RunAutonomyIntakeReviewResponse = {
  run: number;
  candidate_count: number;
  emitted_count: number;
  recommendation_count: number;
};

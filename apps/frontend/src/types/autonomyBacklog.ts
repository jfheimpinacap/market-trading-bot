export type AutonomyBacklogCandidate = {
  advisory_artifact: number;
  advisory_resolution: number;
  insight: number;
  campaign: number | null;
  campaign_title: string | null;
  target_scope: string;
  resolution_status: string;
  ready_for_backlog: boolean;
  existing_backlog_item: number | null;
  blockers: string[];
  metadata: Record<string, unknown>;
};

export type GovernanceBacklogItem = {
  id: number;
  advisory_artifact: number;
  advisory_resolution: number;
  insight: number;
  campaign: number | null;
  campaign_title?: string | null;
  backlog_type: string;
  backlog_status: string;
  priority_level: string;
  target_scope: string;
  summary: string;
  rationale: string;
  reason_codes: string[];
  blockers: string[];
  created_by: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type BacklogRecommendation = {
  id: number;
  advisory_artifact: number | null;
  insight: number | null;
  backlog_item: number | null;
  recommendation_type: string;
  backlog_type: string;
  rationale: string;
  reason_codes: string[];
  confidence: string;
  blockers: string[];
  created_at: string;
};

export type AutonomyBacklogSummary = {
  latest_run_id: number | null;
  candidate_count: number;
  ready_count: number;
  blocked_count: number;
  created_count: number;
  duplicate_skipped_count: number;
  prioritized_count: number;
  recommendation_summary: Record<string, number>;
  total_items: number;
  critical_items: number;
  prioritized_items: number;
  deferred_items: number;
};

export type RunAutonomyBacklogReviewResponse = {
  run: number;
  candidate_count: number;
  created_count: number;
  recommendation_count: number;
};

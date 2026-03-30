export type SeedReviewCandidate = {
  governance_seed: number;
  governance_package: number;
  linked_decisions: number[];
  target_scope: string;
  seed_status: string;
  downstream_status: string;
  ready_for_resolution: boolean;
  blockers: string[];
  metadata: Record<string, unknown>;
};

export type SeedResolution = {
  id: number;
  governance_seed: number;
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

export type SeedReviewRecommendation = {
  id: number;
  review_run: number | null;
  governance_seed: number | null;
  recommendation_type: string;
  rationale: string;
  reason_codes: string[];
  confidence: string;
  blockers: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type SeedReviewSummary = {
  latest_run_id: number | null;
  seed_count: number;
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

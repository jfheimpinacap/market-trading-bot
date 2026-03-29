export type AutonomyAdvisoryResolutionCandidate = {
  advisory_artifact: number;
  insight: number;
  campaign: number | null;
  campaign_title: string | null;
  artifact_type: string;
  artifact_status: string;
  target_scope: string;
  downstream_status: string;
  ready_for_resolution: boolean;
  blockers: string[];
  metadata: Record<string, unknown>;
};

export type AdvisoryResolution = {
  id: number;
  advisory_artifact: number;
  insight: number;
  campaign: number | null;
  campaign_title?: string | null;
  resolution_status: string;
  resolution_type: string;
  rationale: string;
  reason_codes: string[];
  blockers: string[];
  resolved_by: string;
  resolved_at: string | null;
  linked_artifact: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type AdvisoryResolutionRecommendation = {
  id: number;
  advisory_artifact: number | null;
  insight: number | null;
  recommendation_type: string;
  rationale: string;
  reason_codes: string[];
  confidence: string;
  blockers: string[];
  created_at: string;
};

export type AutonomyAdvisoryResolutionSummary = {
  latest_run_id: number | null;
  advisory_emitted_count: number;
  candidate_count: number;
  pending_count: number;
  acknowledged_count: number;
  adopted_count: number;
  deferred_count: number;
  rejected_count: number;
  blocked_count: number;
  closed_count: number;
  recommendation_summary: Record<string, number>;
};

export type RunAutonomyAdvisoryResolutionReviewResponse = {
  run: number;
  candidate_count: number;
  resolution_count: number;
  recommendation_count: number;
};

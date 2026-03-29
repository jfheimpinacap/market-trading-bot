export type AutonomyAdvisoryCandidate = {
  insight: number;
  campaign: number | null;
  campaign_title: string | null;
  insight_type: string;
  recommendation_target: string;
  recommendation_type: string;
  review_status: string;
  ready_for_emission: boolean;
  existing_artifact: number | null;
  blockers: string[];
  metadata: Record<string, unknown>;
};

export type AdvisoryArtifact = {
  id: number;
  insight: number;
  campaign: number | null;
  campaign_title?: string | null;
  artifact_type: string;
  artifact_status: string;
  target_scope: string;
  summary: string;
  rationale: string;
  reason_codes: string[];
  blockers: string[];
  emitted_by: string;
  emitted_at: string | null;
  linked_memory_document: number | null;
  linked_feedback_artifact: string;
  linked_program_note: string;
  created_at: string;
};

export type AdvisoryRecommendation = {
  id: number;
  campaign_insight: number | null;
  target_campaign: number | null;
  campaign_title?: string | null;
  recommendation_type: string;
  artifact_type: string;
  rationale: string;
  reason_codes: string[];
  confidence: string;
  blockers: string[];
  created_at: string;
};

export type AutonomyAdvisorySummary = {
  latest_run_id: number | null;
  candidate_count: number;
  ready_count: number;
  blocked_count: number;
  emitted_count: number;
  duplicate_skipped_count: number;
  memory_note_count: number;
  roadmap_note_count: number;
  scenario_note_count: number;
  program_note_count: number;
  manager_note_count: number;
  recommendation_summary: Record<string, number>;
};

export type RunAutonomyAdvisoryReviewResponse = {
  run: number;
  candidate_count: number;
  recommendation_count: number;
  emitted_count: number;
};

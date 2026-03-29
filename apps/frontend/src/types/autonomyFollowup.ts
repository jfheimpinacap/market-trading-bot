export type FollowupReadiness = 'READY' | 'PARTIAL' | 'BLOCKED' | 'ALREADY_EMITTED';

export type AutonomyFollowupCandidate = {
  campaign: number;
  campaign_title: string;
  closeout_report: number;
  closeout_status: string;
  requires_postmortem: boolean;
  requires_memory_index: boolean;
  requires_roadmap_feedback: boolean;
  existing_memory_document: number | null;
  existing_postmortem_request: string | null;
  existing_feedback_artifact: string | null;
  followup_readiness: FollowupReadiness;
  blockers: string[];
  metadata: Record<string, unknown>;
};

export type CampaignFollowup = {
  id: number;
  campaign: number;
  campaign_title?: string;
  closeout_report: number;
  followup_type: 'MEMORY_INDEX' | 'POSTMORTEM_REQUEST' | 'ROADMAP_FEEDBACK';
  followup_status: 'PENDING_REVIEW' | 'READY' | 'EMITTED' | 'BLOCKED' | 'DUPLICATE_SKIPPED' | 'FAILED';
  rationale: string;
  reason_codes: string[];
  blockers: string[];
  emitted_by: string;
  emitted_at: string | null;
  linked_memory_document: number | null;
  linked_postmortem_request: number | null;
  linked_feedback_artifact: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type FollowupRecommendation = {
  id: number;
  recommendation_type: string;
  target_campaign: number | null;
  target_campaign_title?: string | null;
  followup_type: string;
  rationale: string;
  reason_codes: string[];
  confidence: string;
  blockers: string[];
  created_at: string;
};

export type FollowupSummary = {
  latest_run_id: number | null;
  candidate_count: number;
  ready_count: number;
  blocked_count: number;
  emitted_count: number;
  duplicate_skipped_count: number;
  memory_followup_count: number;
  postmortem_followup_count: number;
  roadmap_feedback_count: number;
  recommendation_summary: Record<string, number>;
};

export type RunFollowupReviewResponse = {
  run: number;
  candidate_count: number;
  recommendation_count: number;
};

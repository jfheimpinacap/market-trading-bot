export type DownstreamStatus = 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'BLOCKED' | 'REJECTED' | 'UNKNOWN';
export type ResolutionStatus = 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'BLOCKED' | 'REJECTED' | 'CLOSED';

export type AutonomyFeedbackCandidate = {
  campaign: number;
  campaign_title: string;
  followup: number;
  followup_type: 'MEMORY_INDEX' | 'POSTMORTEM_REQUEST' | 'ROADMAP_FEEDBACK';
  followup_status: string;
  linked_artifact: string | null;
  downstream_status: DownstreamStatus;
  ready_for_resolution: boolean;
  blockers: string[];
  metadata: Record<string, unknown>;
};

export type FollowupResolution = {
  id: number;
  campaign: number;
  campaign_title?: string;
  followup: number;
  followup_type?: string;
  resolution_status: ResolutionStatus;
  downstream_status: DownstreamStatus;
  resolution_type: string;
  rationale: string;
  reason_codes: string[];
  blockers: string[];
  resolved_by: string;
  resolved_at: string | null;
  linked_memory_document: number | null;
  linked_postmortem_request: number | null;
  linked_feedback_artifact: string;
  created_at: string;
  updated_at: string;
};

export type FeedbackRecommendation = {
  id: number;
  recommendation_type: string;
  target_campaign: number | null;
  target_campaign_title?: string | null;
  followup: number | null;
  followup_type: string;
  rationale: string;
  reason_codes: string[];
  confidence: string;
  blockers: string[];
  created_at: string;
};

export type FeedbackSummary = {
  latest_run_id: number | null;
  candidate_count: number;
  pending_count: number;
  in_progress_count: number;
  completed_count: number;
  blocked_count: number;
  rejected_count: number;
  closed_loop_count: number;
  recommendation_summary: Record<string, number>;
};

export type RunFeedbackReviewResponse = {
  run: number;
  candidate_count: number;
  resolution_count: number;
  recommendation_count: number;
};

export type RecoveryStatus = 'READY_TO_RESUME' | 'RECOVERY_IN_PROGRESS' | 'KEEP_PAUSED' | 'BLOCKED' | 'REVIEW_ABORT' | 'CLOSE_CANDIDATE';
export type ResumeReadiness = 'READY' | 'CAUTION' | 'NOT_READY';

export type RecoveryCandidate = {
  campaign: number;
  campaign_title: string;
  campaign_status: string;
  last_intervention_request: number | null;
  last_intervention_action: number | null;
  last_intervention_outcome: number | null;
  paused_or_blocked_since: string | null;
  current_wave: number | null;
  current_step: number | null;
  open_blockers: string[];
  pending_approvals_count: number;
  pending_checkpoints_count: number;
  incident_impact: number;
  degraded_impact: number;
  rollout_observation_impact: number;
  recovery_status: RecoveryStatus;
  metadata: {
    resume_readiness: ResumeReadiness;
    recovery_priority: number;
  };
};

export type RecoverySnapshot = {
  id: number;
  campaign: number;
  campaign_title?: string;
  base_campaign_status: string;
  last_progress_at: string | null;
  paused_duration_seconds: number | null;
  blocker_count: number;
  blocker_types: Record<string, number>;
  approvals_pending: boolean;
  checkpoints_pending: boolean;
  incident_pressure_level: number;
  recovery_score: string;
  recovery_priority: number;
  resume_readiness: ResumeReadiness;
  recovery_status: RecoveryStatus;
  rationale: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type RecoveryRecommendation = {
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

export type RecoverySummary = {
  latest_run_id: number | null;
  candidate_count: number;
  ready_to_resume_count: number;
  keep_paused_count: number;
  blocked_count: number;
  review_abort_count: number;
  close_candidate_count: number;
  approval_required_count: number;
  recommendation_summary: Record<string, number>;
};

export type RunRecoveryReviewResponse = {
  run: number;
  snapshot_count: number;
  recommendation_count: number;
};

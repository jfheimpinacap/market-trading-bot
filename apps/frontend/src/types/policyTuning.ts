export type PolicyTuningCandidateStatus = 'DRAFT' | 'PENDING_APPROVAL' | 'APPROVED' | 'REJECTED' | 'APPLIED' | 'SUPERSEDED';

export type PolicyTuningReviewDecision = 'APPROVE' | 'REJECT' | 'REQUIRE_MORE_EVIDENCE' | 'DEFER';

export type PolicyChangeSet = {
  id: number;
  candidate: number;
  profile_slug: string;
  action_type: string;
  old_trust_tier: string;
  new_trust_tier: string;
  old_conditions: Record<string, unknown>;
  new_conditions: Record<string, unknown>;
  apply_scope: string;
  notes: string;
  metadata: Record<string, unknown>;
  diff: {
    trust_tier: { current: string; proposed: string };
    conditions: { current: Record<string, unknown>; proposed: Record<string, unknown> };
  };
};

export type PolicyTuningReview = {
  id: number;
  candidate: number;
  decision: PolicyTuningReviewDecision;
  review_status: string;
  reviewer_note: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type PolicyTuningApplicationLog = {
  id: number;
  candidate: number;
  applied_to_profile: number | null;
  applied_to_rule: number | null;
  before_snapshot: Record<string, unknown>;
  after_snapshot: Record<string, unknown>;
  applied_at: string;
  result_summary: string;
  metadata: Record<string, unknown>;
};

export type PolicyTuningCandidate = {
  id: number;
  recommendation: number | null;
  approval_request: number | null;
  action_type: string;
  current_profile: number | null;
  current_rule: number | null;
  current_trust_tier: string;
  proposed_trust_tier: string;
  proposed_conditions: Record<string, unknown>;
  rationale: string;
  confidence: string;
  evidence_refs: Array<Record<string, unknown>>;
  status: PolicyTuningCandidateStatus;
  metadata: Record<string, unknown>;
  created_at: string;
  change_set: PolicyChangeSet;
  reviews: PolicyTuningReview[];
  application_logs: PolicyTuningApplicationLog[];
};

export type PolicyTuningSummary = {
  total_candidates: number;
  pending_candidates: number;
  approved_not_applied: number;
  applied_recently: number;
  rejected_or_superseded: number;
  status_breakdown: Record<string, number>;
  latest_application: { id: number; candidate_id: number; applied_at: string } | null;
};

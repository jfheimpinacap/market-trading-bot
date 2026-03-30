export type PromotionRecommendationCode =
  | 'KEEP_CURRENT_CHAMPION'
  | 'PROMOTE_CHALLENGER'
  | 'EXTEND_SHADOW_TEST'
  | 'REVERT_TO_CONSERVATIVE_STACK'
  | 'MANUAL_REVIEW_REQUIRED';

export type PromotionDecisionLog = {
  id: number;
  review_run: number;
  event_type: string;
  actor: string;
  notes: string;
  payload: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type StackEvidenceSnapshot = {
  id: number;
  champion_binding: { id: number; name: string; execution_profile: string };
  challenger_binding: { id: number; name: string; execution_profile: string } | null;
  champion_challenger_summary: Record<string, unknown>;
  execution_aware_metrics: Record<string, number | string>;
  readiness_summary: Record<string, unknown>;
  profile_governance_context: Record<string, unknown>;
  portfolio_governor_context: Record<string, unknown>;
  model_governance_summary: Record<string, unknown>;
  precedent_warnings: Array<Record<string, unknown>>;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type PromotionReviewRun = {
  id: number;
  status: 'COMPLETED' | 'FAILED';
  decision_mode: 'RECOMMENDATION_ONLY' | 'MANUAL_APPLY';
  readiness_status: string;
  evidence_snapshot: StackEvidenceSnapshot;
  recommendation_code: PromotionRecommendationCode;
  confidence: string;
  rationale: string;
  reason_codes: string[];
  blocking_constraints: string[];
  evidence_summary: Record<string, unknown>;
  summary: string;
  metadata: Record<string, unknown>;
  decision_logs: PromotionDecisionLog[];
  created_at: string;
  updated_at: string;
};

export type PromotionSummary = {
  latest_run: PromotionReviewRun | null;
  total_runs: number;
  recommendation_counts: Record<string, number>;
  is_recommendation_stale: boolean;
};

export type PromotionCaseStatus =
  | 'PROPOSED'
  | 'READY_FOR_REVIEW'
  | 'NEEDS_MORE_DATA'
  | 'DEFERRED'
  | 'REJECTED'
  | 'APPROVED_FOR_MANUAL_ADOPTION';

export type PromotionEvidenceStatus = 'STRONG' | 'MIXED' | 'WEAK' | 'INSUFFICIENT';

export type PromotionDecisionRecommendationType =
  | 'APPROVE_FOR_MANUAL_ADOPTION'
  | 'DEFER_FOR_MORE_EVIDENCE'
  | 'REJECT_CHANGE'
  | 'REQUIRE_COMMITTEE_REVIEW'
  | 'SPLIT_SCOPE_AND_RETEST'
  | 'GROUP_WITH_RELATED_CHANGES'
  | 'REORDER_PROMOTION_PRIORITY';

export type PromotionReviewCycleRun = {
  id: number;
  started_at: string;
  completed_at: string | null;
  linked_experiment_run: number | null;
  candidate_count: number;
  ready_for_review_count: number;
  needs_more_data_count: number;
  deferred_count: number;
  rejected_count: number;
  high_priority_count: number;
  recommendation_summary: Record<string, number>;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type PromotionCase = {
  id: number;
  review_run: number;
  linked_experiment_candidate: number | null;
  linked_comparison: number | null;
  linked_tuning_proposal: number | null;
  linked_bundle: number | null;
  target_component: string;
  target_scope: string;
  change_type: string;
  case_status: PromotionCaseStatus;
  priority_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  current_value: string;
  proposed_value: string;
  rationale: string;
  blockers: string[];
  reason_codes: string[];
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type PromotionEvidencePack = {
  id: number;
  linked_promotion_case: number;
  summary: string;
  linked_metrics: Record<string, unknown>;
  linked_comparisons: Record<string, unknown>;
  linked_recommendations: Record<string, unknown>;
  sample_count: number;
  confidence_score: string;
  risk_of_adoption_score: string;
  expected_benefit_score: string;
  evidence_status: PromotionEvidenceStatus;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type PromotionDecisionRecommendation = {
  id: number;
  review_run: number;
  target_case: number | null;
  recommendation_type: PromotionDecisionRecommendationType;
  rationale: string;
  reason_codes: string[];
  confidence: string;
  blockers: string[];
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type GovernedPromotionSummary = {
  latest_run: PromotionReviewCycleRun | null;
  cases_reviewed: number;
  ready_for_review: number;
  needs_more_data: number;
  deferred: number;
  rejected: number;
  high_priority: number;
  recommendation_summary: Record<string, number>;
};

export type AdoptionActionCandidate = {
  id: number;
  linked_promotion_case: number;
  adoption_run: number;
  target_component: string;
  target_scope: string;
  change_type: string;
  current_value: string;
  proposed_value: string;
  target_resolution_status: 'RESOLVED' | 'PARTIAL' | 'BLOCKED' | 'UNKNOWN';
  ready_for_action: boolean;
  blockers: string[];
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type ManualAdoptionAction = {
  id: number;
  linked_promotion_case: number;
  linked_candidate: number;
  adoption_run: number;
  action_type:
    | 'APPLY_POLICY_TUNING_CHANGE'
    | 'APPLY_TRUST_CALIBRATION_CHANGE'
    | 'APPLY_STACK_BINDING_CHANGE'
    | 'PREPARE_ROLLOUT_PLAN'
    | 'RECORD_MANUAL_ADOPTION'
    | 'REQUIRE_TARGET_MAPPING';
  action_status: 'PROPOSED' | 'READY_TO_APPLY' | 'APPLIED' | 'BLOCKED' | 'DEFERRED' | 'ROLLBACK_AVAILABLE';
  target_component: string;
  target_scope: string;
  current_value_snapshot: Record<string, unknown>;
  proposed_value_snapshot: Record<string, unknown>;
  applied_by: string;
  applied_at: string | null;
  rationale: string;
  reason_codes: string[];
  blockers: string[];
  linked_target_artifact: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type AdoptionRollbackPlan = {
  id: number;
  linked_manual_action: number;
  rollback_type: 'REVERT_VALUE' | 'RESTORE_BINDING' | 'CANCEL_ROLLOUT_PLAN' | 'RETURN_TO_BASELINE';
  rollback_status: 'PREPARED' | 'AVAILABLE' | 'EXECUTED' | 'NOT_NEEDED';
  rollback_target_snapshot: Record<string, unknown>;
  rationale: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type AdoptionActionRecommendation = {
  id: number;
  adoption_run: number;
  linked_promotion_case: number | null;
  target_action: number | null;
  recommendation_type:
    | 'APPLY_CHANGE_MANUALLY'
    | 'PREPARE_ROLLOUT_PLAN'
    | 'REQUIRE_TARGET_MAPPING'
    | 'DEFER_ADOPTION'
    | 'PREPARE_ROLLBACK'
    | 'REQUIRE_COMMITTEE_RECHECK'
    | 'REORDER_ADOPTION_PRIORITY';
  rationale: string;
  reason_codes: string[];
  confidence: string;
  blockers: string[];
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type PromotionAdoptionSummary = {
  latest_run: {
    id: number;
    started_at: string;
    completed_at: string | null;
    linked_promotion_review_run: number | null;
    candidate_count: number;
    ready_to_apply_count: number;
    blocked_count: number;
    applied_count: number;
    rollback_plan_count: number;
    rollout_handoff_count: number;
    recommendation_summary: Record<string, number>;
    metadata: Record<string, unknown>;
    created_at: string;
    updated_at: string;
  } | null;
  approved_cases: number;
  ready_to_apply: number;
  blocked: number;
  applied: number;
  rollback_prepared: number;
  rollout_handoff_ready: number;
  recommendation_summary: Record<string, number>;
};

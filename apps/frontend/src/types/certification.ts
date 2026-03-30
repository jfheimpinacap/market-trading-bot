export type CertificationLevel =
  | 'NOT_CERTIFIED'
  | 'PAPER_CERTIFIED_DEFENSIVE'
  | 'PAPER_CERTIFIED_BALANCED'
  | 'PAPER_CERTIFIED_HIGH_AUTONOMY'
  | 'RECERTIFICATION_REQUIRED'
  | 'REMEDIATION_REQUIRED';

export type CertificationRecommendationCode =
  | 'HOLD_CURRENT_CERTIFICATION'
  | 'UPGRADE_PAPER_AUTONOMY'
  | 'DOWNGRADE_TO_DEFENSIVE'
  | 'REQUIRE_REMEDIATION'
  | 'REQUIRE_RECERTIFICATION'
  | 'MANUAL_REVIEW_REQUIRED';

export type OperatingEnvelope = {
  id: number;
  max_autonomy_mode_allowed: string;
  max_new_entries_per_cycle: number;
  max_size_multiplier_allowed: string;
  auto_execution_allowed: boolean;
  canary_rollout_allowed: boolean;
  aggressive_profiles_disallowed: boolean;
  defensive_profiles_only: boolean;
  allowed_profiles: string[];
  constrained_modules: string[];
  notes: string;
  constraints: string[];
};

export type CertificationEvidenceSnapshot = {
  id: number;
  readiness_summary: Record<string, unknown>;
  execution_evaluation_summary: Record<string, unknown>;
  champion_challenger_summary: Record<string, unknown>;
  promotion_summary: Record<string, unknown>;
  rollout_summary: Record<string, unknown>;
  incident_summary: Record<string, unknown>;
  chaos_benchmark_summary: Record<string, unknown>;
  portfolio_governor_summary: Record<string, unknown>;
  profile_manager_summary: Record<string, unknown>;
  runtime_safety_summary: Record<string, unknown>;
  degraded_or_rollback_summary: Record<string, unknown>;
  metadata: Record<string, unknown>;
};

export type CertificationRun = {
  id: number;
  status: 'COMPLETED' | 'FAILED';
  decision_mode: string;
  certification_level: CertificationLevel;
  recommendation_code: CertificationRecommendationCode;
  confidence: string;
  rationale: string;
  reason_codes: string[];
  blocking_constraints: string[];
  remediation_items: string[];
  evidence_summary: Record<string, unknown>;
  summary: string;
  evidence_snapshot: CertificationEvidenceSnapshot;
  operating_envelope: OperatingEnvelope;
  created_at: string;
};

export type CertificationSummary = {
  latest_run: CertificationRun | null;
  recent_runs: CertificationRun[];
  total_runs: number;
  level_counts: Record<string, number>;
  recommendation_counts: Record<string, number>;
  post_rollout_review?: RolloutCertificationRun | null;
};

export type RolloutCertificationRun = {
  id: number;
  started_at: string;
  completed_at: string | null;
  linked_rollout_execution_run: number | null;
  candidate_count: number;
  certified_count: number;
  observation_count: number;
  review_required_count: number;
  rollback_recommended_count: number;
  rejected_count: number;
  recommendation_summary: Record<string, number>;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type CertificationCandidate = {
  id: number;
  review_run: number;
  linked_rollout_execution: number;
  linked_post_rollout_status: number | null;
  linked_rollout_plan: number;
  linked_promotion_case: number | null;
  target_component: string;
  target_scope: string;
  rollout_status: string;
  stabilization_readiness: string;
  blockers: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type CertificationEvidencePack = {
  id: number;
  linked_candidate: number;
  summary: string;
  linked_checkpoint_outcomes: Array<Record<string, unknown>>;
  linked_post_rollout_statuses: Array<Record<string, unknown>>;
  linked_evaluation_metrics: Record<string, unknown>;
  sample_count: number;
  confidence_score: string;
  stability_score: string;
  regression_risk_score: string;
  evidence_status: 'STRONG' | 'MIXED' | 'WEAK' | 'INSUFFICIENT';
  metadata: Record<string, unknown>;
  created_at: string;
};

export type CertificationDecision = {
  id: number;
  linked_candidate: number;
  linked_evidence_pack: number;
  decision_status: string;
  rationale: string;
  reason_codes: string[];
  blockers: string[];
  decided_by: string;
  decided_at: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type CertificationRecommendationItem = {
  id: number;
  review_run: number;
  target_candidate: number | null;
  recommendation_type: string;
  rationale: string;
  reason_codes: string[];
  confidence: string;
  blockers: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type PostRolloutCertificationSummary = {
  latest_run: RolloutCertificationRun | null;
  candidate_count: number;
  certified_count: number;
  observation_count: number;
  review_required_count: number;
  rollback_recommended_count: number;
  rejected_count: number;
  recommendation_summary: Record<string, number>;
  decision_counts: Record<string, number>;
};

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

export type BaselineConfirmationRun = {
  id: number;
  started_at: string;
  completed_at: string | null;
  linked_certification_run: number | null;
  candidate_count: number;
  ready_to_confirm_count: number;
  blocked_count: number;
  confirmed_count: number;
  rollback_ready_count: number;
  recommendation_summary: Record<string, number>;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type BaselineConfirmationCandidate = {
  id: number;
  review_run: number;
  linked_certification_decision: number;
  linked_certification_candidate: number;
  linked_rollout_execution: number | null;
  target_component: string;
  target_scope: string;
  certification_status: string;
  previous_baseline_reference: string;
  proposed_baseline_reference: string;
  binding_resolution_status: 'RESOLVED' | 'PARTIAL' | 'BLOCKED' | 'UNKNOWN';
  ready_for_confirmation: boolean;
  blockers: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type PaperBaselineConfirmation = {
  id: number;
  linked_candidate: number;
  linked_certification_decision: number;
  confirmation_status: string;
  target_component: string;
  target_scope: string;
  previous_baseline_snapshot: Record<string, unknown>;
  confirmed_baseline_snapshot: Record<string, unknown>;
  confirmed_by: string;
  confirmed_at: string | null;
  rationale: string;
  reason_codes: string[];
  blockers: string[];
  linked_binding_artifact: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type BaselineBindingSnapshot = {
  id: number;
  linked_confirmation: number;
  binding_type: string;
  binding_status: 'PREVIOUS' | 'PROPOSED' | 'CONFIRMED' | 'REVERTED';
  binding_snapshot: Record<string, unknown>;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type BaselineConfirmationRecommendationItem = {
  id: number;
  review_run: number;
  target_confirmation: number | null;
  recommendation_type: string;
  rationale: string;
  reason_codes: string[];
  confidence: string;
  blockers: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type BaselineConfirmationSummary = {
  latest_run: BaselineConfirmationRun | null;
  candidate_count: number;
  ready_to_confirm_count: number;
  blocked_count: number;
  confirmed_count: number;
  rollback_ready_count: number;
  binding_review_required_count: number;
  recommendation_summary: Record<string, number>;
};


export type BaselineActivationRun = {
  id: number;
  started_at: string;
  completed_at: string | null;
  linked_baseline_confirmation_run: number | null;
  candidate_count: number;
  ready_to_activate_count: number;
  blocked_count: number;
  activated_count: number;
  rollback_ready_count: number;
  recommendation_summary: Record<string, number>;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type BaselineActivationCandidate = {
  id: number;
  review_run: number;
  linked_paper_baseline_confirmation: number;
  linked_certification_decision: number | null;
  target_component: string;
  target_scope: string;
  previous_active_reference: string;
  proposed_active_reference: string;
  activation_resolution_status: 'RESOLVED' | 'PARTIAL' | 'BLOCKED' | 'UNKNOWN';
  ready_for_activation: boolean;
  blockers: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type PaperBaselineActivation = {
  id: number;
  linked_candidate: number | null;
  linked_confirmation: number;
  activation_status: string;
  target_component: string;
  target_scope: string;
  previous_active_snapshot: Record<string, unknown>;
  activated_snapshot: Record<string, unknown>;
  activated_by: string;
  activated_at: string | null;
  rationale: string;
  reason_codes: string[];
  blockers: string[];
  linked_binding_artifact: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type ActivePaperBindingRecord = {
  id: number;
  target_component: string;
  target_scope: string;
  active_binding_type: string;
  active_snapshot: Record<string, unknown>;
  source_activation: number | null;
  status: 'ACTIVE' | 'SUPERSEDED' | 'REVERTED';
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type BaselineActivationRecommendationItem = {
  id: number;
  review_run: number;
  target_activation: number | null;
  recommendation_type: string;
  rationale: string;
  reason_codes: string[];
  confidence: string;
  blockers: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type BaselineActivationSummary = {
  latest_run: BaselineActivationRun | null;
  confirmed_baselines: number;
  candidate_count: number;
  ready_to_activate_count: number;
  blocked_count: number;
  activated_count: number;
  rollback_available_count: number;
  binding_recheck_required_count: number;
  recommendation_summary: Record<string, number>;
};

export type BaselineHealthRun = {
  id: number;
  started_at: string;
  completed_at: string | null;
  linked_baseline_activation_run: number | null;
  active_binding_count: number;
  healthy_count: number;
  watch_count: number;
  degraded_count: number;
  review_required_count: number;
  rollback_review_count: number;
  recommendation_summary: Record<string, number>;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type BaselineHealthCandidate = {
  id: number;
  review_run: number;
  linked_active_binding: number;
  linked_baseline_activation: number | null;
  target_component: string;
  target_scope: string;
  active_binding_type: string;
  current_health_inputs: Record<string, unknown>;
  readiness_status: 'READY' | 'NEEDS_MORE_DATA' | 'BLOCKED';
  blockers: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type BaselineHealthStatus = {
  id: number;
  linked_candidate: number;
  health_status:
    | 'HEALTHY'
    | 'UNDER_WATCH'
    | 'DEGRADED'
    | 'REVIEW_REQUIRED'
    | 'ROLLBACK_REVIEW_RECOMMENDED'
    | 'INSUFFICIENT_DATA';
  calibration_health_score: string;
  risk_gate_health_score: string;
  opportunity_quality_health_score: string;
  drift_risk_score: string;
  regression_risk_score: string;
  rationale: string;
  reason_codes: string[];
  blockers: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type BaselineHealthSignal = {
  id: number;
  linked_status: number;
  signal_type: string;
  signal_severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  signal_direction: 'improving' | 'stable' | 'degrading';
  evidence_summary: Record<string, unknown>;
  rationale: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type BaselineHealthRecommendationItem = {
  id: number;
  review_run: number;
  target_status: number | null;
  recommendation_type: string;
  rationale: string;
  reason_codes: string[];
  confidence: string;
  blockers: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type BaselineHealthSummary = {
  latest_run: BaselineHealthRun | null;
  active_baselines_reviewed: number;
  healthy_count: number;
  under_watch_count: number;
  degraded_count: number;
  review_required_count: number;
  rollback_review_recommended_count: number;
  recommendation_summary: Record<string, number>;
};

export type BaselineResponseRun = {
  id: number;
  started_at: string;
  completed_at: string | null;
  linked_baseline_health_run: number | null;
  candidate_count: number;
  opened_case_count: number;
  watch_case_count: number;
  reevaluation_case_count: number;
  tuning_case_count: number;
  rollback_review_case_count: number;
  recommendation_summary: Record<string, number>;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type BaselineResponseCase = {
  id: number;
  review_run: number;
  linked_active_binding: number | null;
  linked_baseline_health_status: number | null;
  linked_health_signals: Array<Record<string, unknown>>;
  target_component: string;
  target_scope: string;
  response_type:
    | 'KEEP_UNDER_WATCH'
    | 'OPEN_REEVALUATION'
    | 'OPEN_TUNING_REVIEW'
    | 'REQUIRE_MANUAL_BASELINE_REVIEW'
    | 'PREPARE_ROLLBACK_REVIEW'
    | 'REQUIRE_COMMITTEE_RECHECK';
  priority_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  case_status: 'OPEN' | 'UNDER_REVIEW' | 'ROUTED' | 'DEFERRED' | 'CLOSED_NO_ACTION' | 'ESCALATED';
  rationale: string;
  reason_codes: string[];
  blockers: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type ResponseEvidencePack = {
  id: number;
  linked_response_case: number;
  summary: string;
  linked_health_status: number | null;
  linked_health_signals: Array<Record<string, unknown>>;
  linked_evaluation_metrics: Record<string, unknown>;
  linked_risk_context: Record<string, unknown>;
  linked_opportunity_context: Record<string, unknown>;
  confidence_score: string;
  severity_score: string;
  urgency_score: string;
  evidence_status: 'STRONG' | 'MIXED' | 'WEAK' | 'INSUFFICIENT';
  metadata: Record<string, unknown>;
  created_at: string;
};

export type ResponseRoutingDecision = {
  id: number;
  linked_response_case: number;
  routing_target:
    | 'evaluation_lab'
    | 'tuning_board'
    | 'promotion_committee'
    | 'certification_board'
    | 'rollback_review'
    | 'monitoring_only';
  routing_status: 'PROPOSED' | 'READY' | 'SENT' | 'DEFERRED' | 'BLOCKED';
  routing_rationale: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type BaselineResponseRecommendationItem = {
  id: number;
  review_run: number;
  target_case: number | null;
  recommendation_type: string;
  rationale: string;
  reason_codes: string[];
  confidence: string;
  blockers: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type BaselineResponseSummary = {
  latest_run: BaselineResponseRun | null;
  active_baselines_reviewed: number;
  open_response_cases: number;
  reevaluation_case_count: number;
  tuning_case_count: number;
  rollback_review_case_count: number;
  watch_case_count: number;
  recommendation_summary: Record<string, number>;
  case_status_summary: Record<string, number>;
  routing_status_summary: Record<string, number>;
  evidence_status_summary: Record<string, number>;
  recommendation_type_summary: Record<string, number>;
};

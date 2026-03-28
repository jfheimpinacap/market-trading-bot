export type AutonomyStage = 'MANUAL' | 'ASSISTED' | 'SUPERVISED_AUTOPILOT' | 'FROZEN' | 'ROLLBACK_RECOMMENDED';

export type AutonomyDomainStatus = 'ACTIVE' | 'OBSERVING' | 'DEGRADED' | 'BLOCKED';

export type AutonomyRecommendationCode =
  | 'PROMOTE_TO_ASSISTED'
  | 'PROMOTE_TO_SUPERVISED_AUTOPILOT'
  | 'KEEP_CURRENT_STAGE'
  | 'DOWNGRADE_TO_MANUAL'
  | 'FREEZE_DOMAIN'
  | 'REQUIRE_MORE_DATA'
  | 'ROLLBACK_STAGE';

export type AutonomyTransitionStatus = 'DRAFT' | 'PENDING_APPROVAL' | 'READY_TO_APPLY' | 'APPLIED' | 'ROLLED_BACK';

export type AutonomyEnvelope = {
  max_auto_actions_per_cycle: number;
  approval_override_behavior: string;
  blocked_contexts: string[];
  degraded_mode_handling: string;
  certification_dependencies: string[];
  runtime_dependencies: string[];
  metadata: Record<string, unknown>;
};

export type AutonomyDomain = {
  id: number;
  slug: string;
  name: string;
  description: string;
  owner_app: string;
  action_types: string[];
  source_apps: string[];
  metadata: Record<string, unknown>;
  envelope: AutonomyEnvelope | null;
};

export type AutonomyState = {
  id: number;
  domain: number;
  domain_slug: string;
  domain_name: string;
  current_stage: AutonomyStage;
  effective_stage: AutonomyStage;
  status: AutonomyDomainStatus;
  rationale: string;
  linked_policy_profiles: string[];
  linked_action_types: string[];
  last_changed_at: string;
  metadata: Record<string, unknown>;
};

export type AutonomyTransition = {
  id: number;
  domain: number;
  domain_slug: string;
  state: number;
  recommendation: number | null;
  approval_request: number | null;
  status: AutonomyTransitionStatus;
  previous_stage: AutonomyStage;
  requested_stage: AutonomyStage;
  applied_stage: AutonomyStage | '';
  rationale: string;
  reason_codes: string[];
  evidence_refs: Array<Record<string, unknown>>;
  requested_by: string;
  applied_by: string;
  rolled_back_by: string;
  applied_at: string | null;
  rolled_back_at: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type AutonomyRecommendation = {
  id: number;
  domain: number;
  domain_slug: string;
  state: number | null;
  recommendation_code: AutonomyRecommendationCode;
  current_stage: AutonomyStage;
  proposed_stage: AutonomyStage;
  rationale: string;
  reason_codes: string[];
  confidence: string;
  evidence_refs: Array<Record<string, unknown>>;
  metadata: Record<string, unknown>;
  created_at: string;
  transition: AutonomyTransition | null;
};

export type AutonomySummary = {
  total_domains: number;
  manual_domains: number;
  assisted_domains: number;
  supervised_autopilot_domains: number;
  frozen_domains: number;
  degraded_domains: number;
  blocked_domains: number;
  pending_stage_changes: number;
  applied_transitions: number;
  rolled_back_transitions: number;
};

export type AutonomyReviewResult = {
  summary: AutonomySummary;
  recommendations_generated: number;
  transitions_generated: number;
  recommendations: AutonomyRecommendation[];
};

import type { AutonomyStage } from './autonomy';

export type DomainCriticality = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type DomainDependencyType = 'requires_stable' | 'blocks_if_degraded' | 'recommended_before' | 'incompatible_parallel';

export type RoadmapRecommendationAction =
  | 'PROMOTE_DOMAIN'
  | 'HOLD_DOMAIN'
  | 'FREEZE_DOMAIN'
  | 'ROLLBACK_DOMAIN'
  | 'SEQUENCE_BEFORE'
  | 'DO_NOT_PROMOTE_IN_PARALLEL'
  | 'REQUIRE_STABILIZATION_FIRST';

export type AutonomyRoadmapDependency = {
  id: number;
  source_domain: number;
  source_domain_slug: string;
  source_criticality: DomainCriticality;
  target_domain: number;
  target_domain_slug: string;
  target_criticality: DomainCriticality;
  dependency_type: DomainDependencyType;
  rationale: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type RoadmapRecommendation = {
  id: number;
  plan: number;
  plan_id: number;
  domain: number;
  domain_slug: string;
  current_stage: AutonomyStage;
  proposed_stage: AutonomyStage;
  action: RoadmapRecommendationAction;
  rationale: string;
  reason_codes: string[];
  confidence: string;
  evidence_refs: Array<Record<string, unknown>>;
  created_at: string;
};

export type RoadmapBundle = {
  id: number;
  plan: number;
  name: string;
  domains: string[];
  sequence_order: string[];
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
  requires_approval: boolean;
  rationale: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type AutonomyRoadmapPlan = {
  id: number;
  summary: string;
  current_domain_posture: Record<string, unknown>;
  candidate_transitions: Array<Record<string, unknown>>;
  blocked_domains: string[];
  frozen_domains: string[];
  recommended_sequence: string[];
  recommendations: RoadmapRecommendation[];
  bundles: RoadmapBundle[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type AutonomyRoadmapSummary = {
  total_plans: number;
  latest_plan_id: number | null;
  latest_summary: string | null;
  latest_blocked_domains: string[];
  latest_frozen_domains: string[];
  latest_recommended_sequence: string[];
  recommendation_breakdown: Record<string, number>;
  latest_plan: AutonomyRoadmapPlan | null;
};

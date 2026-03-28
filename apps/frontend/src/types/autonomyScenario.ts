export type ScenarioRecommendationCode =
  | 'BEST_NEXT_MOVE'
  | 'SAFE_BUNDLE'
  | 'SEQUENCE_FIRST'
  | 'DELAY_UNTIL_STABLE'
  | 'DO_NOT_EXECUTE'
  | 'REQUIRE_APPROVAL_HEAVY';

export type ScenarioOption = {
  id: number;
  run: number;
  option_key: string;
  option_type: string;
  domains: string[];
  order: string[];
  requested_stages: Record<string, string>;
  is_bundle: boolean;
  notes: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type ScenarioRiskEstimate = {
  id: number;
  run: number;
  option: number;
  option_key: string;
  dependency_conflict_risk: string;
  approval_friction_risk: string;
  degraded_posture_risk: string;
  incident_exposure_risk: string;
  rollback_likelihood_hint: string;
  bundle_risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
  confidence: string;
  approval_heavy: boolean;
  conflicts: Array<Record<string, unknown>>;
  blockers: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type ScenarioRecommendation = {
  id: number;
  run: number;
  option: number;
  option_key: string;
  recommendation_code: ScenarioRecommendationCode;
  rationale: string;
  reason_codes: string[];
  supporting_evidence: Array<Record<string, unknown>>;
  estimated_blockers: string[];
  score: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type AutonomyScenarioRun = {
  id: number;
  summary: string;
  evidence_snapshot: Record<string, unknown>;
  selected_option_key: string;
  selected_recommendation_code: ScenarioRecommendationCode | '';
  metadata: Record<string, unknown>;
  options: ScenarioOption[];
  risk_estimates: ScenarioRiskEstimate[];
  recommendations: ScenarioRecommendation[];
  created_at: string;
};

export type AutonomyScenarioSummary = {
  total_runs: number;
  latest_run_id: number | null;
  latest_summary: string | null;
  latest_selected_option_key: string | null;
  latest_recommendation_code: ScenarioRecommendationCode | null;
  recommendation_breakdown: Record<string, number>;
};

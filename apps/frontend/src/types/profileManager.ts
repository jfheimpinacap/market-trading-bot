export type ProfileRegime = 'NORMAL' | 'CAUTION' | 'STRESSED' | 'CONCENTRATED' | 'DRAWDOWN_MODE' | 'DEFENSIVE' | 'BLOCKED' | string;
export type ProfileDecisionMode = 'RECOMMEND_ONLY' | 'APPLY_SAFE' | 'APPLY_FORCED' | string;

export type ManagedProfileBinding = {
  id: number;
  module_key: string;
  operating_mode: string;
  profile_slug: string;
  profile_label: string;
  is_active: boolean;
  metadata: Record<string, unknown>;
};

export type ProfileDecision = {
  id: number;
  decision_mode: ProfileDecisionMode;
  target_research_profile: string;
  target_signal_profile: string;
  target_opportunity_supervisor_profile: string;
  target_mission_control_profile: string;
  target_portfolio_governor_profile: string;
  target_prediction_profile: string;
  rationale: string;
  reason_codes: string[];
  blocking_constraints: string[];
  metadata: Record<string, unknown>;
  is_applied: boolean;
  applied_at: string | null;
  created_at: string;
};

export type ProfileGovernanceRun = {
  id: number;
  status: string;
  regime: ProfileRegime;
  runtime_mode: string;
  readiness_status: string;
  safety_status: string;
  triggered_by: string;
  started_at: string;
  finished_at: string | null;
  summary: string;
  details: Record<string, unknown>;
  decision: ProfileDecision | null;
};

export type ProfileGovernanceSummary = {
  latest_run: number | null;
  current_regime: ProfileRegime;
  decision_mode: ProfileDecisionMode;
  is_applied: boolean;
  target_profiles: Record<string, string>;
  blocking_constraints: string[];
  reason_codes: string[];
  runtime_mode: string;
  readiness_status: string;
  safety_status: string;
  available_bindings: ManagedProfileBinding[];
  paper_demo_only: boolean;
  real_execution_enabled: boolean;
};

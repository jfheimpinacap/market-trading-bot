export type ChallengerRecommendationCode = 'KEEP_CHAMPION' | 'CHALLENGER_PROMISING' | 'CHALLENGER_UNDERPERFORMS' | 'REVIEW_MANUALLY';

export type StackProfileBinding = {
  id: number;
  name: string;
  is_champion: boolean;
  is_active: boolean;
  prediction_model_artifact: number | null;
  prediction_profile_slug: string;
  research_profile_slug: string;
  signal_profile_slug: string;
  opportunity_supervisor_profile_slug: string;
  mission_control_profile_slug: string;
  portfolio_governor_profile_slug: string;
  execution_profile: string;
  runtime_constraints_snapshot: Record<string, unknown>;
  notes: string;
  created_at: string;
  updated_at: string;
};

export type ShadowComparisonResult = {
  id: number;
  run: number;
  champion_metrics: Record<string, number | string>;
  challenger_metrics: Record<string, number | string>;
  deltas: Record<string, number | string>;
  decision_divergence_rate: string;
};

export type ChampionChallengerRun = {
  id: number;
  champion_binding: StackProfileBinding;
  challenger_binding: StackProfileBinding;
  status: 'RUNNING' | 'COMPLETED' | 'FAILED';
  started_at: string;
  finished_at: string | null;
  markets_evaluated: number;
  opportunities_compared: number;
  proposals_compared: number;
  fills_compared: number;
  pnl_delta_execution_adjusted: string;
  recommendation_code: ChallengerRecommendationCode;
  recommendation_reasons: string[];
  summary: string;
  details: Record<string, unknown>;
  comparison_result?: ShadowComparisonResult;
  created_at: string;
  updated_at: string;
};

export type ChampionChallengerSummary = {
  current_champion: StackProfileBinding;
  latest_run: ChampionChallengerRun | null;
  recent_runs: ChampionChallengerRun[];
  total_runs: number;
  completed_runs: number;
};

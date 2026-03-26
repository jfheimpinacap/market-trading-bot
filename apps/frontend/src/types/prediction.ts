export type PredictionProfile = {
  id: number;
  slug: string;
  name: string;
  description: string;
  is_active: boolean;
  use_narrative: boolean;
  use_learning: boolean;
  calibration_alpha: string;
  calibration_beta: string;
  confidence_floor: string;
  confidence_cap: string;
  edge_strong_threshold: string;
  edge_neutral_threshold: string;
  weights: Record<string, number>;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type PredictionRun = {
  id: number;
  status: string;
  triggered_by: string;
  profile_slug: string;
  started_at: string;
  finished_at: string | null;
  markets_scored: number;
  errors: string[];
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type PredictionScore = {
  id: number;
  run: PredictionRun;
  market: number;
  market_slug: string;
  market_title: string;
  profile_slug: string;
  market_probability: string;
  system_probability: string;
  edge: string;
  edge_label: 'positive' | 'negative' | 'neutral' | string;
  confidence: string;
  confidence_level: 'low' | 'medium' | 'high' | string;
  rationale: string;
  narrative_contribution: string;
  model_profile_used: string;
  details: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type ScoreMarketPayload = {
  market_id: number;
  profile_slug?: string;
  triggered_by?: string;
};

export type PredictionSummary = {
  profile_count: number;
  total_scores: number;
  avg_edge: string | null;
  avg_confidence: string | null;
  latest_score: PredictionScore | null;
};

export type PredictionDatasetRun = {
  id: number;
  name: string;
  status: string;
  label_definition: string;
  feature_set_version: string;
  rows_built: number;
  positive_rows: number;
  negative_rows: number;
  snapshot_horizon_hours: number;
  summary: string;
  created_at: string;
  updated_at: string;
};

export type PredictionTrainingRun = {
  id: number;
  status: string;
  model_type: string;
  rows_used: number;
  artifact_created: boolean;
  validation_summary: Record<string, unknown>;
  summary: string;
  started_at: string;
  finished_at: string | null;
  dataset_run: PredictionDatasetRun;
  created_at: string;
  updated_at: string;
};

export type PredictionModelArtifact = {
  id: number;
  name: string;
  version: string;
  model_type: string;
  label_definition: string;
  feature_set_version: string;
  is_active: boolean;
  validation_metrics: Record<string, unknown>;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type PredictionTrainingSummary = {
  latest_dataset: PredictionDatasetRun | null;
  active_model: PredictionModelArtifact | null;
  training_runs_by_status: Record<string, number>;
  models_total: number;
};

export type ModelEvaluationProfile = {
  id: number;
  slug: string;
  name: string;
  description: string;
  is_active: boolean;
  config: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type ModelComparisonResult = {
  id: number;
  predictor_key: string;
  predictor_label: string;
  predictor_type: string;
  profile_slug: string;
  metrics: Record<string, number>;
  failures: number;
  coverage: string;
};

export type ModelComparisonRun = {
  id: number;
  status: string;
  scope: 'demo_only' | 'real_only' | 'mixed' | string;
  baseline_key: string;
  candidate_key: string;
  winner: string;
  recommendation_code: string;
  recommendation_reasons: string[];
  metrics_summary: Record<string, number>;
  created_at: string;
  evaluation_profile: ModelEvaluationProfile;
  results: ModelComparisonResult[];
};

export type ActiveModelRecommendation = {
  recommendation_code: string;
  recommendation_reasons: string[];
  comparison_run_id: number | null;
  winner?: string;
};

export type ModelGovernanceSummary = {
  active_model: { id: number; name: string; version: string; model_type: string } | null;
  latest_comparison: Record<string, unknown> | null;
  recent_recommendations: Array<Record<string, unknown>>;
};

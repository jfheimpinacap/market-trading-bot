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

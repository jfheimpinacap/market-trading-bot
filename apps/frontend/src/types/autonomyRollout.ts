export type AutonomyRolloutStatus = 'OBSERVING' | 'STABLE' | 'CAUTION' | 'FREEZE_RECOMMENDED' | 'ROLLBACK_RECOMMENDED' | 'COMPLETED' | 'ABORTED';

export type AutonomyRolloutRecommendationCode = 'KEEP_STAGE' | 'REQUIRE_MORE_DATA' | 'FREEZE_DOMAIN' | 'ROLLBACK_STAGE' | 'REVIEW_MANUALLY' | 'STABILIZE_AND_MONITOR';

export type AutonomyRolloutBaselineSnapshot = {
  id: number;
  run: number;
  metrics: Record<string, string | number>;
  counts: Record<string, number>;
  created_at: string;
};

export type AutonomyRolloutPostChangeSnapshot = {
  id: number;
  run: number;
  metrics: Record<string, string | number>;
  counts: Record<string, number>;
  deltas: Record<string, string | number>;
  confidence: string;
  sample_size: number;
  created_at: string;
};

export type AutonomyRolloutRecommendation = {
  id: number;
  run: number;
  recommendation: AutonomyRolloutRecommendationCode;
  rationale: string;
  reason_codes: string[];
  confidence: string;
  supporting_deltas: Record<string, string | number>;
  warnings: string[];
  cross_domain_notes: Record<string, unknown>[];
  created_at: string;
};

export type AutonomyRolloutRun = {
  id: number;
  autonomy_stage_transition: number;
  domain: number;
  rollout_status: AutonomyRolloutStatus;
  observation_window_days: number;
  summary: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  baseline_snapshot: AutonomyRolloutBaselineSnapshot;
  post_change_snapshot: AutonomyRolloutPostChangeSnapshot | null;
  recommendations: AutonomyRolloutRecommendation[];
};

export type AutonomyRolloutSummary = {
  total_runs: number;
  observing_runs: number;
  stable_runs: number;
  freeze_recommended_runs: number;
  rollback_recommended_runs: number;
  aborted_runs: number;
  latest_run_id: number | null;
  latest_status: AutonomyRolloutStatus | null;
  active_run_id: number | null;
  domains_with_warning: number;
};

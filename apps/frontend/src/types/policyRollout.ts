export type PolicyRolloutStatus = 'OBSERVING' | 'STABLE' | 'CAUTION' | 'ROLLBACK_RECOMMENDED' | 'COMPLETED' | 'ABORTED';

export type PolicyRolloutRecommendationCode = 'KEEP_CHANGE' | 'REQUIRE_MORE_DATA' | 'ROLLBACK_CHANGE' | 'REVIEW_MANUALLY' | 'STABILIZE_AND_MONITOR';

export type PolicyRolloutBaselineSnapshot = {
  id: number;
  run: number;
  metrics: Record<string, string | number>;
  counts: Record<string, number>;
  created_at: string;
};

export type PolicyRolloutPostChangeSnapshot = {
  id: number;
  run: number;
  metrics: Record<string, string | number>;
  counts: Record<string, number>;
  deltas: Record<string, string | number>;
  confidence: string;
  sample_size: number;
  created_at: string;
};

export type PolicyRolloutRecommendation = {
  id: number;
  run: number;
  recommendation: PolicyRolloutRecommendationCode;
  rationale: string;
  reason_codes: string[];
  confidence: string;
  supporting_deltas: Record<string, string | number>;
  blockers: string[];
  warnings: string[];
  created_at: string;
};

export type PolicyRolloutRun = {
  id: number;
  policy_tuning_candidate: number;
  application_log: number;
  rollout_status: PolicyRolloutStatus;
  observation_window_days: number;
  summary: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  baseline_snapshot: PolicyRolloutBaselineSnapshot;
  post_change_snapshot: PolicyRolloutPostChangeSnapshot | null;
  recommendations: PolicyRolloutRecommendation[];
};

export type PolicyRolloutSummary = {
  total_runs: number;
  observing_runs: number;
  stable_runs: number;
  rollback_recommended_runs: number;
  aborted_runs: number;
  latest_run_id: number | null;
  latest_status: PolicyRolloutStatus | null;
  active_run_id: number | null;
};

export type TuningExperimentRunResponse = {
  run_id: number;
  candidate_count: number;
  comparison_count: number;
  recommendation_summary: Record<string, number>;
};

export type ExperimentCandidate = {
  id: number;
  run: number;
  linked_tuning_proposal: number;
  linked_tuning_bundle: number | null;
  candidate_type: string;
  baseline_reference: string;
  challenger_label: string;
  experiment_scope: string;
  readiness_status: 'READY' | 'NEEDS_MORE_DATA' | 'BLOCKED' | 'DEFERRED';
  rationale: string;
  blockers: string[];
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type ChampionChallengerComparison = {
  id: number;
  run: number;
  linked_candidate: number;
  baseline_label: string;
  challenger_label: string;
  comparison_status: 'IMPROVED' | 'DEGRADED' | 'MIXED' | 'INCONCLUSIVE' | 'NEEDS_MORE_DATA';
  compared_metrics: Record<string, string>;
  sample_count: number;
  confidence_score: string;
  rationale: string;
  reason_codes: string[];
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type ExperimentPromotionRecommendation = {
  id: number;
  run: number;
  target_candidate: number | null;
  target_comparison: number | null;
  recommendation_type:
    | 'PROMOTE_TO_MANUAL_REVIEW'
    | 'KEEP_BASELINE'
    | 'REQUIRE_MORE_DATA'
    | 'REJECT_CHALLENGER'
    | 'BUNDLE_WITH_OTHER_CHANGES'
    | 'REORDER_EXPERIMENT_PRIORITY';
  rationale: string;
  reason_codes: string[];
  confidence: string;
  blockers: string[];
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type TuningValidationSummary = {
  latest_run: number | null;
  candidates_reviewed: number;
  comparisons_run: number;
  improved: number;
  degraded: number;
  inconclusive: number;
  ready_for_manual_review: number;
  recommendation_summary: Record<string, number>;
  manual_first: boolean;
  paper_only: boolean;
  auto_promotion: boolean;
};

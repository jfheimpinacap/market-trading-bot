export type TuningProposalStatus = 'PROPOSED' | 'WATCH' | 'READY_FOR_REVIEW' | 'DEFERRED' | 'REJECTED' | 'EXPIRED';
export type TuningPriorityLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export type TuningReviewRun = {
  id: number;
  linked_evaluation_run: number | null;
  metrics_reviewed_count: number;
  poor_metric_count: number;
  drift_flag_count: number;
  proposal_count: number;
  high_priority_proposal_count: number;
  recommendation_summary: Record<string, number>;
  metadata: Record<string, unknown>;
  started_at: string;
  completed_at: string | null;
};

export type TuningProposal = {
  id: number;
  run: number;
  source_metric: number | null;
  source_recommendation: number | null;
  proposal_type: string;
  target_scope: string;
  target_component: string;
  target_value: string;
  current_value: string | null;
  proposed_value: string | null;
  proposal_status: TuningProposalStatus;
  evidence_strength_score: string;
  priority_level: TuningPriorityLevel;
  rationale: string;
  reason_codes: string[];
  blockers: string[];
  linked_metrics: number[];
  linked_recommendations: number[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type TuningImpactHypothesis = {
  id: number;
  proposal: number;
  hypothesis_type: string;
  expected_direction: 'increase' | 'decrease' | 'stabilize';
  target_metric_type: string;
  expected_effect_size: string | null;
  rationale: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type TuningRecommendation = {
  id: number;
  run: number;
  target_proposal: number | null;
  recommendation_type: string;
  rationale: string;
  reason_codes: string[];
  confidence: string;
  blockers: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type TuningBundle = {
  id: number;
  run: number;
  bundle_label: string;
  bundle_scope: string;
  linked_proposals: number[];
  bundle_status: string;
  rationale: string;
  metadata: Record<string, unknown>;
};

export type TuningSummary = {
  latest_run: TuningReviewRun | null;
  metrics_reviewed: number;
  proposals_generated: number;
  ready_for_review: number;
  need_more_data: number;
  bundled_proposals: number;
  critical_priority: number;
};

import { requestJson } from './api/client';

export type EvaluationRuntimeSummary = {
  latest_run: {
    id: number;
    started_at: string;
    completed_at: string | null;
    resolved_market_count: number;
    linked_prediction_count: number;
    linked_risk_count: number;
    linked_proposal_count: number;
    calibration_bucket_count: number;
    metric_count: number;
    drift_flag_count: number;
    recommendation_summary: Record<string, number>;
  } | null;
  manual_review_required: boolean;
  poor_metric_count: number;
  drift_flags: Array<{ flag_type: string; scope: string; segment_value: string; value: string; reason: string }>;
  recommendations: EvaluationRecommendation[];
};

export type OutcomeAlignmentRecord = {
  id: number;
  market_title: string;
  market_provider: string;
  market_category: string;
  linked_prediction_assessment: number | null;
  linked_risk_approval: number | null;
  linked_opportunity_assessment: number | null;
  linked_paper_proposal: number | null;
  resolved_outcome: string;
  market_probability_at_decision: string | null;
  calibrated_probability_at_decision: string | null;
  adjusted_edge_at_decision: string | null;
  risk_status_at_decision: string;
  proposal_status_at_decision: string;
  alignment_status: string;
  metadata: Record<string, unknown>;
};

export type CalibrationBucket = {
  id: number;
  bucket_label: string;
  sample_count: number;
  mean_predicted_probability: string;
  empirical_hit_rate: string;
  calibration_gap: string;
  segment_scope: string;
  segment_value: string;
};

export type EffectivenessMetric = {
  id: number;
  metric_type: string;
  metric_scope: string;
  metric_value: string;
  sample_count: number;
  interpretation: string;
  status: string;
  metadata: Record<string, unknown>;
};

export type EvaluationRecommendation = {
  id: number;
  recommendation_type: string;
  target_metric: number | null;
  rationale: string;
  reason_codes: string[];
  confidence: string;
};

export function runRuntimeEvaluation() {
  return requestJson('/api/evaluation/run-runtime-evaluation/', {
    method: 'POST',
    body: JSON.stringify({}),
  });
}

export function getOutcomeAlignmentRecords(params?: Record<string, string>) {
  const query = params ? `?${new URLSearchParams(params).toString()}` : '';
  return requestJson<OutcomeAlignmentRecord[]>(`/api/evaluation/outcome-alignment/${query}`);
}

export function getCalibrationBuckets(params?: Record<string, string>) {
  const query = params ? `?${new URLSearchParams(params).toString()}` : '';
  return requestJson<CalibrationBucket[]>(`/api/evaluation/calibration-buckets/${query}`);
}

export function getEffectivenessMetrics(params?: Record<string, string>) {
  const query = params ? `?${new URLSearchParams(params).toString()}` : '';
  return requestJson<EffectivenessMetric[]>(`/api/evaluation/effectiveness-metrics/${query}`);
}

export function getEvaluationRecommendations() {
  return requestJson<EvaluationRecommendation[]>('/api/evaluation/recommendations/');
}

export function getEvaluationRuntimeSummary() {
  return requestJson<EvaluationRuntimeSummary>('/api/evaluation/runtime-summary/');
}

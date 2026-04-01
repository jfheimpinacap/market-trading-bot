import { requestJson } from './api/client';
import type {
  PredictionConvictionReview,
  PredictionIntakeCandidate,
  PredictionIntakeRecommendation,
  PredictionIntakeRun,
  PredictionIntakeSummary,
  PredictionRiskHandoff,
  PredictionRuntimeAssessment,
  PredictionRuntimeCandidate,
  PredictionRuntimeRecommendation,
  PredictionRuntimeRun,
  PredictionRuntimeSummary,
} from '../types/prediction';

export function runPredictionRuntimeReview(payload?: { triggered_by?: string }) {
  return requestJson<PredictionRuntimeRun>('/api/prediction/run-runtime-review/', {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function runPredictionIntakeReview(payload?: { triggered_by?: string }) {
  return requestJson<PredictionIntakeRun>('/api/prediction/run-intake-review/', {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function getPredictionIntakeRuns() {
  return requestJson<PredictionIntakeRun[]>('/api/prediction/intake-runs/');
}

export function getPredictionIntakeCandidates(runId?: number) {
  const query = runId ? `?run_id=${runId}` : '';
  return requestJson<PredictionIntakeCandidate[]>(`/api/prediction/intake-candidates/${query}`);
}

export function getPredictionConvictionReviews(runId?: number) {
  const query = runId ? `?run_id=${runId}` : '';
  return requestJson<PredictionConvictionReview[]>(`/api/prediction/conviction-reviews/${query}`);
}

export function getPredictionRiskHandoffs(runId?: number) {
  const query = runId ? `?run_id=${runId}` : '';
  return requestJson<PredictionRiskHandoff[]>(`/api/prediction/risk-handoffs/${query}`);
}

export function getPredictionIntakeRecommendations(runId?: number) {
  const query = runId ? `?run_id=${runId}` : '';
  return requestJson<PredictionIntakeRecommendation[]>(`/api/prediction/intake-recommendations/${query}`);
}

export function getPredictionIntakeSummary() {
  return requestJson<PredictionIntakeSummary>('/api/prediction/intake-summary/');
}

export function getPredictionRuntimeCandidates(runId?: number) {
  const query = runId ? `?run_id=${runId}` : '';
  return requestJson<PredictionRuntimeCandidate[]>(`/api/prediction/runtime-candidates/${query}`);
}

export function getPredictionRuntimeAssessments(params?: { runId?: number; status?: string }) {
  const query = new URLSearchParams();
  if (params?.runId) query.set('run_id', String(params.runId));
  if (params?.status) query.set('status', params.status);
  const suffix = query.toString() ? `?${query.toString()}` : '';
  return requestJson<PredictionRuntimeAssessment[]>(`/api/prediction/runtime-assessments/${suffix}`);
}

export function getPredictionRuntimeRecommendations(params?: { runId?: number; recommendationType?: string }) {
  const query = new URLSearchParams();
  if (params?.runId) query.set('run_id', String(params.runId));
  if (params?.recommendationType) query.set('recommendation_type', params.recommendationType);
  const suffix = query.toString() ? `?${query.toString()}` : '';
  return requestJson<PredictionRuntimeRecommendation[]>(`/api/prediction/runtime-recommendations/${suffix}`);
}

export function getPredictionRuntimeSummary() {
  return requestJson<PredictionRuntimeSummary>('/api/prediction/runtime-summary/');
}

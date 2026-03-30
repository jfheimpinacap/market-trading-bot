import { requestJson } from './api/client';
import type {
  ChampionChallengerComparison,
  ExperimentCandidate,
  ExperimentPromotionRecommendation,
  TuningExperimentRunResponse,
  TuningValidationSummary,
} from '../types/tuningValidation';

export function runTuningValidation(payload?: { linked_tuning_review_run_id?: number; metadata?: Record<string, unknown> }) {
  return requestJson<TuningExperimentRunResponse>('/api/experiments/run-tuning-validation/', {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function getTuningExperimentCandidates(params?: { component?: string; scope?: string; readiness_status?: string }) {
  const query = new URLSearchParams();
  if (params?.component) query.set('component', params.component);
  if (params?.scope) query.set('scope', params.scope);
  if (params?.readiness_status) query.set('readiness_status', params.readiness_status);
  return requestJson<ExperimentCandidate[]>(`/api/experiments/tuning-candidates/${query.toString() ? `?${query.toString()}` : ''}`);
}

export function getChampionChallengerComparisons(params?: { comparison_status?: string }) {
  const query = new URLSearchParams();
  if (params?.comparison_status) query.set('comparison_status', params.comparison_status);
  return requestJson<ChampionChallengerComparison[]>(`/api/experiments/champion-challenger-comparisons/${query.toString() ? `?${query.toString()}` : ''}`);
}

export function getExperimentPromotionRecommendations() {
  return requestJson<ExperimentPromotionRecommendation[]>('/api/experiments/promotion-recommendations/');
}

export function getTuningValidationSummary() {
  return requestJson<TuningValidationSummary>('/api/experiments/tuning-validation-summary/');
}

import { requestJson } from './api/client';
import type {
  ActivePaperBindingRecord,
  BaselineActivationCandidate,
  BaselineActivationRecommendationItem,
  BaselineActivationSummary,
  PaperBaselineActivation,
} from '../types/certification';

export function runBaselineActivationReview(payload: Record<string, unknown> = {}) {
  return requestJson<{
    candidate_count: number;
    activation_count: number;
    recommendation_count: number;
  }>('/api/certification/run-baseline-activation/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getBaselineActivationCandidates() {
  return requestJson<BaselineActivationCandidate[]>('/api/certification/activation-candidates/');
}

export function getBaselineActivations() {
  return requestJson<PaperBaselineActivation[]>('/api/certification/baseline-activations/');
}

export function getActivePaperBindings() {
  return requestJson<ActivePaperBindingRecord[]>('/api/certification/active-bindings/');
}

export function getBaselineActivationRecommendations() {
  return requestJson<BaselineActivationRecommendationItem[]>('/api/certification/activation-recommendations/');
}

export function getBaselineActivationSummary() {
  return requestJson<BaselineActivationSummary>('/api/certification/activation-summary/');
}

export function activatePaperBaseline(confirmationId: number, payload: Record<string, unknown> = {}) {
  return requestJson<PaperBaselineActivation>(`/api/certification/activate-baseline/${confirmationId}/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function rollbackActivation(activationId: number, payload: Record<string, unknown> = {}) {
  return requestJson<PaperBaselineActivation>(`/api/certification/rollback-activation/${activationId}/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

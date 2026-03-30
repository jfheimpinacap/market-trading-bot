import { requestJson } from './api/client';
import type {
  BaselineBindingSnapshot,
  BaselineConfirmationCandidate,
  BaselineConfirmationRecommendationItem,
  BaselineConfirmationSummary,
  PaperBaselineConfirmation,
} from '../types/certification';

export function runBaselineConfirmationReview(payload: Record<string, unknown> = {}) {
  return requestJson<{
    candidate_count: number;
    confirmation_count: number;
    recommendation_count: number;
  }>('/api/certification/run-baseline-confirmation/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getBaselineConfirmationCandidates() {
  return requestJson<BaselineConfirmationCandidate[]>('/api/certification/baseline-candidates/');
}

export function getBaselineConfirmations() {
  return requestJson<PaperBaselineConfirmation[]>('/api/certification/baseline-confirmations/');
}

export function getBaselineBindingSnapshots() {
  return requestJson<BaselineBindingSnapshot[]>('/api/certification/binding-snapshots/');
}

export function getBaselineRecommendations() {
  return requestJson<BaselineConfirmationRecommendationItem[]>('/api/certification/baseline-recommendations/');
}

export function getBaselineSummary() {
  return requestJson<BaselineConfirmationSummary>('/api/certification/baseline-summary/');
}

export function confirmPaperBaseline(decisionId: number, payload: Record<string, unknown> = {}) {
  return requestJson<PaperBaselineConfirmation>(`/api/certification/confirm-baseline/${decisionId}/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function rollbackPaperBaseline(confirmationId: number, payload: Record<string, unknown> = {}) {
  return requestJson<PaperBaselineConfirmation>(`/api/certification/rollback-baseline/${confirmationId}/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

import { requestJson } from './api/client';
import type {
  GovernedPromotionSummary,
  PromotionCase,
  PromotionDecisionRecommendation,
  PromotionEvidencePack,
  PromotionReviewCycleRun,
} from '../types/promotion';

export function runPromotionReview(payload: Record<string, unknown> = {}) {
  return requestJson<PromotionReviewCycleRun>('/api/promotion/run-review/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getPromotionCases(query: Record<string, string> = {}) {
  const params = new URLSearchParams(query);
  const suffix = params.toString() ? `?${params.toString()}` : '';
  return requestJson<PromotionCase[]>(`/api/promotion/cases/${suffix}`);
}

export function getPromotionEvidencePacks() {
  return requestJson<PromotionEvidencePack[]>('/api/promotion/evidence-packs/');
}

export function getPromotionRecommendations() {
  return requestJson<PromotionDecisionRecommendation[]>('/api/promotion/recommendations/');
}

export function getPromotionSummary() {
  return requestJson<GovernedPromotionSummary>('/api/promotion/summary/');
}

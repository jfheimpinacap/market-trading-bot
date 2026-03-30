import { requestJson } from './api/client';
import type { PromotionReviewRun, PromotionSummary } from '../types/promotion';

export function runPromotionReview(payload: Record<string, unknown>) {
  return requestJson<PromotionReviewRun>('/api/promotion/legacy-run-review/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getPromotionRuns() {
  return requestJson<PromotionReviewRun[]>('/api/promotion/runs/');
}

export function getPromotionRun(id: number) {
  return requestJson<PromotionReviewRun>(`/api/promotion/runs/${id}/`);
}

export function getCurrentPromotionRecommendation() {
  return requestJson<{ current_recommendation: PromotionReviewRun | null }>('/api/promotion/current-recommendation/');
}

export function getPromotionSummary() {
  return requestJson<PromotionSummary>('/api/promotion/legacy-summary/');
}

export function applyPromotionDecision(id: number, payload: Record<string, unknown> = {}) {
  return requestJson<PromotionReviewRun>(`/api/promotion/apply/${id}/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

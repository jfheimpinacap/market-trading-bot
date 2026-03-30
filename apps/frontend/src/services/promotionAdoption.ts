import { requestJson } from './api/client';
import type {
  AdoptionActionCandidate,
  AdoptionActionRecommendation,
  AdoptionRollbackPlan,
  ManualAdoptionAction,
  PromotionAdoptionSummary,
} from '../types/promotion';

export function runPromotionAdoptionReview(payload: Record<string, unknown> = {}) {
  return requestJson('/api/promotion/run-adoption-review/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getPromotionAdoptionCandidates() {
  return requestJson<AdoptionActionCandidate[]>('/api/promotion/adoption-candidates/');
}

export function getPromotionAdoptionActions() {
  return requestJson<ManualAdoptionAction[]>('/api/promotion/adoption-actions/');
}

export function getPromotionRollbackPlans() {
  return requestJson<AdoptionRollbackPlan[]>('/api/promotion/rollback-plans/');
}

export function getPromotionAdoptionRecommendations() {
  return requestJson<AdoptionActionRecommendation[]>('/api/promotion/adoption-recommendations/');
}

export function getPromotionAdoptionSummary() {
  return requestJson<PromotionAdoptionSummary>('/api/promotion/adoption-summary/');
}

export function applyPromotionCase(caseId: number, payload: Record<string, unknown> = {}) {
  return requestJson<ManualAdoptionAction>(`/api/promotion/apply/${caseId}/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

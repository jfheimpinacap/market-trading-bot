import { requestJson } from './api/client';
import type {
  ManualRollbackExecution,
  ManualRolloutPlan,
  PromotionRolloutSummary,
  RolloutActionCandidate,
  RolloutCheckpointPlan,
  RolloutPreparationRecommendation,
} from '../types/promotion';

export function runPromotionRolloutPrep(payload: Record<string, unknown> = {}) {
  return requestJson('/api/promotion/run-rollout-prep/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getPromotionRolloutCandidates() {
  return requestJson<RolloutActionCandidate[]>('/api/promotion/rollout-candidates/');
}

export function getPromotionRolloutPlans() {
  return requestJson<ManualRolloutPlan[]>('/api/promotion/rollout-plans/');
}

export function getPromotionCheckpointPlans() {
  return requestJson<RolloutCheckpointPlan[]>('/api/promotion/checkpoint-plans/');
}

export function getPromotionRollbackExecutions() {
  return requestJson<ManualRollbackExecution[]>('/api/promotion/rollback-executions/');
}

export function getPromotionRolloutRecommendations() {
  return requestJson<RolloutPreparationRecommendation[]>('/api/promotion/rollout-recommendations/');
}

export function getPromotionRolloutSummary() {
  return requestJson<PromotionRolloutSummary>('/api/promotion/rollout-summary/');
}

export function preparePromotionRollout(caseId: number, payload: Record<string, unknown> = {}) {
  return requestJson(`/api/promotion/prepare-rollout/${caseId}/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function rollbackPromotionAction(actionId: number, payload: Record<string, unknown> = {}) {
  return requestJson<ManualRollbackExecution>(`/api/promotion/rollback/${actionId}/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

import { requestJson } from './api/client';
import type {
  CheckpointOutcomeRecord,
  PostRolloutStatus,
  PromotionRolloutExecutionSummary,
  RolloutExecutionRecord,
  RolloutExecutionRecommendation,
  RolloutExecutionRun,
} from '../types/promotion';

export function runPromotionRolloutExecutionReview(payload: Record<string, unknown> = {}) {
  return requestJson<RolloutExecutionRun>('/api/promotion/run-rollout-execution/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getPromotionRolloutExecutions() {
  return requestJson<RolloutExecutionRecord[]>('/api/promotion/rollout-executions/');
}

export function getPromotionCheckpointOutcomes() {
  return requestJson<CheckpointOutcomeRecord[]>('/api/promotion/checkpoint-outcomes/');
}

export function getPromotionPostRolloutStatus() {
  return requestJson<PostRolloutStatus[]>('/api/promotion/post-rollout-status/');
}

export function getPromotionRolloutExecutionRecommendations() {
  return requestJson<RolloutExecutionRecommendation[]>('/api/promotion/rollout-execution-recommendations/');
}

export function getPromotionRolloutExecutionSummary() {
  return requestJson<PromotionRolloutExecutionSummary>('/api/promotion/rollout-execution-summary/');
}

export function executePromotionRollout(planId: number, payload: Record<string, unknown> = {}) {
  return requestJson(`/api/promotion/execute-rollout/${planId}/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function recordPromotionCheckpointOutcome(checkpointId: number, payload: Record<string, unknown>) {
  return requestJson(`/api/promotion/record-checkpoint-outcome/${checkpointId}/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function closePromotionRollout(executionId: number, payload: Record<string, unknown> = {}) {
  return requestJson(`/api/promotion/close-rollout/${executionId}/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

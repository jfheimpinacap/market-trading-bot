import { requestJson } from './api/client';
import type { LearningAdjustment, LearningIntegrationStatus, LearningMemoryEntry, LearningRebuildRun, LearningSummary } from '../types/learning';

export function getLearningSummary() {
  return requestJson<LearningSummary>('/api/learning/summary/');
}

export function getLearningMemory() {
  return requestJson<LearningMemoryEntry[]>('/api/learning/memory/');
}

export function getLearningAdjustments() {
  return requestJson<LearningAdjustment[]>('/api/learning/adjustments/');
}

export function rebuildLearningMemory() {
  return requestJson<LearningRebuildRun>('/api/learning/rebuild/', {
    method: 'POST',
    body: JSON.stringify({}),
  });
}

export function getLearningRebuildRuns() {
  return requestJson<LearningRebuildRun[]>('/api/learning/rebuild-runs/');
}

export function getLearningRebuildRun(id: number | string) {
  return requestJson<LearningRebuildRun>(`/api/learning/rebuild-runs/${id}/`);
}

export function getLearningIntegrationStatus() {
  return requestJson<LearningIntegrationStatus>('/api/learning/integration-status/');
}

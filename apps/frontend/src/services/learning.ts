import { requestJson } from './api/client';
import type { LearningAdjustment, LearningMemoryEntry, LearningSummary } from '../types/learning';

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
  return requestJson<{ status: string; created_memory_entries: number; adjustments_processed: number }>('/api/learning/rebuild/', {
    method: 'POST',
    body: JSON.stringify({}),
  });
}

import { requestJson } from './api/client';
import type {
  FailurePattern,
  LearningAdjustment,
  LearningApplicationRecord,
  LearningLoopSummary,
  LearningRecommendation,
  PostmortemLearningRun,
} from '../types/learning';

export function runPostmortemLearningLoop(linkedPostmortemRunId?: number) {
  return requestJson<PostmortemLearningRun>('/api/learning/run-postmortem-loop/', {
    method: 'POST',
    body: JSON.stringify(linkedPostmortemRunId ? { linked_postmortem_run_id: linkedPostmortemRunId } : {}),
  });
}

export function getFailurePatterns() {
  return requestJson<FailurePattern[]>('/api/learning/failure-patterns/');
}

export function getLearningAdjustments() {
  return requestJson<LearningAdjustment[]>('/api/learning/adjustments/');
}

export function getLearningApplicationRecords() {
  return requestJson<LearningApplicationRecord[]>('/api/learning/application-records/');
}

export function getLearningRecommendations() {
  return requestJson<LearningRecommendation[]>('/api/learning/recommendations/');
}

export function getPostmortemLearningSummary() {
  return requestJson<LearningLoopSummary>('/api/learning/postmortem-loop-summary/');
}

import { requestJson } from './api/client';
import type {
  DownstreamAcknowledgement,
  DownstreamLifecycleOutcome,
  ResponseLifecycleRecommendationItem,
  ResponseLifecycleSummary,
  ResponseReviewStageRecord,
} from '../types/certification';

export function runBaselineResponseLifecycle(input: { actor?: string; metadata?: Record<string, unknown> } = {}) {
  return requestJson('/api/certification/run-baseline-response-lifecycle/', {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export function getDownstreamAcknowledgements() {
  return requestJson<DownstreamAcknowledgement[]>('/api/certification/downstream-acknowledgements/');
}

export function getReviewStageRecords() {
  return requestJson<ResponseReviewStageRecord[]>('/api/certification/review-stage-records/');
}

export function getDownstreamLifecycleOutcomes() {
  return requestJson<DownstreamLifecycleOutcome[]>('/api/certification/downstream-lifecycle-outcomes/');
}

export function getResponseLifecycleRecommendations() {
  return requestJson<ResponseLifecycleRecommendationItem[]>('/api/certification/response-lifecycle-recommendations/');
}

export function getResponseLifecycleSummary() {
  return requestJson<ResponseLifecycleSummary>('/api/certification/response-lifecycle-summary/');
}

export function acknowledgeBaselineResponseCase(caseId: number, input: Record<string, unknown>) {
  return requestJson(`/api/certification/acknowledge-response-case/${caseId}/`, {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export function updateBaselineResponseStage(caseId: number, input: Record<string, unknown>) {
  return requestJson(`/api/certification/update-response-stage/${caseId}/`, {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export function recordDownstreamOutcome(caseId: number, input: Record<string, unknown>) {
  return requestJson(`/api/certification/record-downstream-outcome/${caseId}/`, {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

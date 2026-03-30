import { requestJson } from './api/client';
import type {
  BaselineResponseActionSummary,
  ResponseActionCandidate,
  ResponseActionRecommendationItem,
  ResponseCaseTrackingRecord,
  ResponseRoutingAction,
} from '../types/certification';

export function runBaselineResponseActions(input: { actor?: string; metadata?: Record<string, unknown> } = {}) {
  return requestJson('/api/certification/run-baseline-response-actions/', {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export function getBaselineResponseActionCandidates() {
  return requestJson<ResponseActionCandidate[]>('/api/certification/response-action-candidates/');
}

export function getBaselineResponseRoutingActions() {
  return requestJson<ResponseRoutingAction[]>('/api/certification/response-routing-actions/');
}

export function getBaselineResponseTrackingRecords() {
  return requestJson<ResponseCaseTrackingRecord[]>('/api/certification/response-tracking-records/');
}

export function getBaselineResponseActionRecommendations() {
  return requestJson<ResponseActionRecommendationItem[]>('/api/certification/response-action-recommendations/');
}

export function getBaselineResponseActionSummary() {
  return requestJson<BaselineResponseActionSummary>('/api/certification/response-action-summary/');
}

export function routeBaselineResponseCase(caseId: number, input: Record<string, unknown> = {}) {
  return requestJson(`/api/certification/route-response-case/${caseId}/`, {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export function updateBaselineResponseTracking(caseId: number, input: Record<string, unknown>) {
  return requestJson(`/api/certification/update-response-tracking/${caseId}/`, {
    method: 'POST',
    body: JSON.stringify(input),
  });
}


export function closeBaselineResponseCase(caseId: number, input: Record<string, unknown> = {}) {
  return requestJson(`/api/certification/close-response-case/${caseId}/`, {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

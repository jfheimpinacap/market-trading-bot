import { requestJson } from './api/client';
import type {
  BaselineHealthCandidate,
  BaselineHealthRecommendationItem,
  BaselineHealthStatus,
  BaselineHealthSummary,
  BaselineHealthSignal,
} from '../types/certification';

export function runBaselineHealthReview(payload: Record<string, unknown> = {}) {
  return requestJson<{
    candidate_count: number;
    status_count: number;
    signal_count: number;
    recommendation_count: number;
  }>('/api/certification/run-baseline-health-review/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getBaselineHealthCandidates() {
  return requestJson<BaselineHealthCandidate[]>('/api/certification/health-candidates/');
}

export function getBaselineHealthStatuses() {
  return requestJson<BaselineHealthStatus[]>('/api/certification/health-status/');
}

export function getBaselineHealthSignals() {
  return requestJson<BaselineHealthSignal[]>('/api/certification/health-signals/');
}

export function getBaselineHealthRecommendations() {
  return requestJson<BaselineHealthRecommendationItem[]>('/api/certification/health-recommendations/');
}

export function getBaselineHealthSummary() {
  return requestJson<BaselineHealthSummary>('/api/certification/health-summary/');
}

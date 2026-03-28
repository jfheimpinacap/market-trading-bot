import { requestJson } from './api/client';
import type { AutonomyDomain, AutonomyRecommendation, AutonomyReviewResult, AutonomyState, AutonomySummary, AutonomyTransition } from '../types/autonomy';

export function getAutonomyDomains() {
  return requestJson<AutonomyDomain[]>('/api/autonomy/domains/');
}

export function getAutonomyStates() {
  return requestJson<AutonomyState[]>('/api/autonomy/states/');
}

export function getAutonomyRecommendations() {
  return requestJson<AutonomyRecommendation[]>('/api/autonomy/recommendations/');
}

export function runAutonomyReview(payload?: { requested_by?: string }) {
  return requestJson<AutonomyReviewResult>('/api/autonomy/run-review/', {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function applyAutonomyTransition(id: number, payload?: { applied_by?: string }) {
  return requestJson<AutonomyTransition>(`/api/autonomy/transitions/${id}/apply/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function rollbackAutonomyTransition(id: number, payload?: { rolled_back_by?: string }) {
  return requestJson<AutonomyTransition>(`/api/autonomy/transitions/${id}/rollback/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function getAutonomySummary() {
  return requestJson<AutonomySummary>('/api/autonomy/summary/');
}

import { requestJson } from './api/client';
import type { LaunchAuthorization, LaunchCandidate, LaunchReadinessSnapshot, LaunchRecommendation, LaunchRunResponse, LaunchSummary } from '../types/autonomyLaunch';

export function getAutonomyLaunchCandidates() {
  return requestJson<LaunchCandidate[]>('/api/autonomy-launch/candidates/');
}

export function runAutonomyLaunchPreflight(payload?: { actor?: string }) {
  return requestJson<LaunchRunResponse>('/api/autonomy-launch/run-preflight/', {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function getAutonomyLaunchReadiness() {
  return requestJson<LaunchReadinessSnapshot[]>('/api/autonomy-launch/readiness/');
}

export function getAutonomyLaunchRecommendations() {
  return requestJson<LaunchRecommendation[]>('/api/autonomy-launch/recommendations/');
}

export function getAutonomyLaunchAuthorizations() {
  return requestJson<LaunchAuthorization[]>('/api/autonomy-launch/authorizations/');
}

export function getAutonomyLaunchSummary() {
  return requestJson<LaunchSummary>('/api/autonomy-launch/summary/');
}

export function authorizeAutonomyLaunch(campaignId: number, payload?: { actor?: string }) {
  return requestJson<LaunchAuthorization>(`/api/autonomy-launch/authorize/${campaignId}/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function holdAutonomyLaunch(campaignId: number, payload?: { actor?: string; rationale?: string }) {
  return requestJson<LaunchAuthorization>(`/api/autonomy-launch/hold/${campaignId}/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

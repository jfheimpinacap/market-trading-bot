import { requestJson } from './api/client';
import type { GovernanceSeed, SeedCandidate, SeedRecommendation, SeedSummary } from '../types/autonomySeed';

export function getAutonomySeedCandidates() {
  return requestJson<SeedCandidate[]>('/api/autonomy-seed/candidates/');
}

export function runAutonomySeedReview(payload?: { actor?: string }) {
  return requestJson<{ run: number; candidate_count: number; recommendation_count: number }>('/api/autonomy-seed/run-review/', {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function getAutonomySeeds() {
  return requestJson<GovernanceSeed[]>('/api/autonomy-seed/seeds/');
}

export function getAutonomySeedRecommendations() {
  return requestJson<SeedRecommendation[]>('/api/autonomy-seed/recommendations/');
}

export function getAutonomySeedSummary() {
  return requestJson<SeedSummary>('/api/autonomy-seed/summary/');
}

export function registerAutonomySeed(packageId: number, payload?: { actor?: string }) {
  return requestJson<{ seed_id: number; seed_status: string }>(`/api/autonomy-seed/register/${packageId}/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function acknowledgeAutonomySeed(seedId: number, payload?: { actor?: string }) {
  return requestJson<{ seed_id: number; seed_status: string }>(`/api/autonomy-seed/acknowledge/${seedId}/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

import { requestJson } from './api/client';
import type { SeedResolution, SeedReviewCandidate, SeedReviewRecommendation, SeedReviewSummary } from '../types/autonomySeedReview';

export function getAutonomySeedReviewCandidates() {
  return requestJson<SeedReviewCandidate[]>('/api/autonomy-seed-review/candidates/');
}

export function runAutonomySeedReview(payload?: { actor?: string }) {
  return requestJson<{ run: number; candidate_count: number; recommendation_count: number }>('/api/autonomy-seed-review/run-review/', {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function getAutonomySeedReviewResolutions() {
  return requestJson<SeedResolution[]>('/api/autonomy-seed-review/resolutions/');
}

export function getAutonomySeedReviewRecommendations() {
  return requestJson<SeedReviewRecommendation[]>('/api/autonomy-seed-review/recommendations/');
}

export function getAutonomySeedReviewSummary() {
  return requestJson<SeedReviewSummary>('/api/autonomy-seed-review/summary/');
}

export function acknowledgeAutonomySeed(seedId: number, payload?: { actor?: string }) {
  return requestJson<{ seed_id: number; resolution_status: string }>(`/api/autonomy-seed-review/acknowledge/${seedId}/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function acceptAutonomySeed(seedId: number, payload?: { actor?: string }) {
  return requestJson<{ seed_id: number; resolution_status: string }>(`/api/autonomy-seed-review/accept/${seedId}/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function deferAutonomySeed(seedId: number, payload?: { actor?: string }) {
  return requestJson<{ seed_id: number; resolution_status: string }>(`/api/autonomy-seed-review/defer/${seedId}/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function rejectAutonomySeed(seedId: number, payload?: { actor?: string }) {
  return requestJson<{ seed_id: number; resolution_status: string }>(`/api/autonomy-seed-review/reject/${seedId}/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

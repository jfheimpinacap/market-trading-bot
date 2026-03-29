import { requestJson } from './api/client';
import type { PackageReviewCandidate, PackageReviewRecommendation, PackageReviewSummary, PackageResolution } from '../types/autonomyPackageReview';

export function getAutonomyPackageReviewCandidates() {
  return requestJson<PackageReviewCandidate[]>('/api/autonomy-package-review/candidates/');
}

export function runAutonomyPackageReview(payload?: { actor?: string }) {
  return requestJson<{ run: number; candidate_count: number; recommendation_count: number }>('/api/autonomy-package-review/run-review/', {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function getAutonomyPackageReviewResolutions() {
  return requestJson<PackageResolution[]>('/api/autonomy-package-review/resolutions/');
}

export function getAutonomyPackageReviewRecommendations() {
  return requestJson<PackageReviewRecommendation[]>('/api/autonomy-package-review/recommendations/');
}

export function getAutonomyPackageReviewSummary() {
  return requestJson<PackageReviewSummary>('/api/autonomy-package-review/summary/');
}

export function acknowledgeAutonomyPackage(packageId: number, payload?: { actor?: string }) {
  return requestJson<{ package_id: number; resolution_status: string }>(`/api/autonomy-package-review/acknowledge/${packageId}/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function adoptAutonomyPackage(packageId: number, payload?: { actor?: string }) {
  return requestJson<{ package_id: number; resolution_status: string }>(`/api/autonomy-package-review/adopt/${packageId}/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function deferAutonomyPackage(packageId: number, payload?: { actor?: string }) {
  return requestJson<{ package_id: number; resolution_status: string }>(`/api/autonomy-package-review/defer/${packageId}/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function rejectAutonomyPackage(packageId: number, payload?: { actor?: string }) {
  return requestJson<{ package_id: number; resolution_status: string }>(`/api/autonomy-package-review/reject/${packageId}/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

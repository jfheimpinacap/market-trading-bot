import { requestJson } from './api/client';
import type { AutonomyPackageCandidate, AutonomyPackageSummary, GovernancePackage, PackageRecommendation } from '../types/autonomyPackage';

export function getAutonomyPackageCandidates() {
  return requestJson<AutonomyPackageCandidate[]>('/api/autonomy-package/candidates/');
}

export function runAutonomyPackageReview(payload?: { actor?: string }) {
  return requestJson<{ run: number; candidate_count: number; recommendation_count: number }>('/api/autonomy-package/run-review/', {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function getAutonomyPackages() {
  return requestJson<GovernancePackage[]>('/api/autonomy-package/packages/');
}

export function getAutonomyPackageRecommendations() {
  return requestJson<PackageRecommendation[]>('/api/autonomy-package/recommendations/');
}

export function getAutonomyPackageSummary() {
  return requestJson<AutonomyPackageSummary>('/api/autonomy-package/summary/');
}

export function registerAutonomyPackage(decisionId: number, payload?: { actor?: string }) {
  return requestJson<{ package_id: number; package_status: string }>(`/api/autonomy-package/register/${decisionId}/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function acknowledgeAutonomyPackage(packageId: number) {
  return requestJson<{ package_id: number; package_status: string }>(`/api/autonomy-package/acknowledge/${packageId}/`, {
    method: 'POST',
    body: JSON.stringify({}),
  });
}

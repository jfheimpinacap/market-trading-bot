import { requestJson } from './api/client';
import type {
  AdvisoryArtifact,
  AdvisoryRecommendation,
  AutonomyAdvisoryCandidate,
  AutonomyAdvisorySummary,
  RunAutonomyAdvisoryReviewResponse,
} from '../types/autonomyAdvisory';

export function getAutonomyAdvisoryCandidates() {
  return requestJson<AutonomyAdvisoryCandidate[]>('/api/autonomy-advisory/candidates/');
}

export function runAutonomyAdvisoryReview(payload?: { actor?: string }) {
  return requestJson<RunAutonomyAdvisoryReviewResponse>('/api/autonomy-advisory/run-review/', {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function getAutonomyAdvisoryArtifacts() {
  return requestJson<AdvisoryArtifact[]>('/api/autonomy-advisory/artifacts/');
}

export function getAutonomyAdvisoryRecommendations() {
  return requestJson<AdvisoryRecommendation[]>('/api/autonomy-advisory/recommendations/');
}

export function getAutonomyAdvisorySummary() {
  return requestJson<AutonomyAdvisorySummary>('/api/autonomy-advisory/summary/');
}

export function emitAutonomyAdvisory(insightId: number, payload?: { actor?: string }) {
  return requestJson<{ artifact_id: number; artifact_status: string }>(`/api/autonomy-advisory/emit/${insightId}/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

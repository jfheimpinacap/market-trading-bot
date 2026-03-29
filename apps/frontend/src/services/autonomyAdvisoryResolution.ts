import { requestJson } from './api/client';
import type {
  AdvisoryResolution,
  AdvisoryResolutionRecommendation,
  AutonomyAdvisoryResolutionCandidate,
  AutonomyAdvisoryResolutionSummary,
  RunAutonomyAdvisoryResolutionReviewResponse,
} from '../types/autonomyAdvisoryResolution';

export function getAutonomyAdvisoryResolutionCandidates() {
  return requestJson<AutonomyAdvisoryResolutionCandidate[]>('/api/autonomy-advisory-resolution/candidates/');
}

export function runAutonomyAdvisoryResolutionReview(payload?: { actor?: string }) {
  return requestJson<RunAutonomyAdvisoryResolutionReviewResponse>('/api/autonomy-advisory-resolution/run-review/', {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function getAutonomyAdvisoryResolutions() {
  return requestJson<AdvisoryResolution[]>('/api/autonomy-advisory-resolution/resolutions/');
}

export function getAutonomyAdvisoryResolutionRecommendations() {
  return requestJson<AdvisoryResolutionRecommendation[]>('/api/autonomy-advisory-resolution/recommendations/');
}

export function getAutonomyAdvisoryResolutionSummary() {
  return requestJson<AutonomyAdvisoryResolutionSummary>('/api/autonomy-advisory-resolution/summary/');
}

export function acknowledgeAutonomyAdvisory(artifactId: number, payload?: { actor?: string }) {
  return requestJson<{ resolution_id: number; resolution_status: string }>(`/api/autonomy-advisory-resolution/acknowledge/${artifactId}/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function adoptAutonomyAdvisory(artifactId: number, payload?: { actor?: string; rationale?: string; reason_codes?: string[] }) {
  return requestJson<{ resolution_id: number; resolution_status: string }>(`/api/autonomy-advisory-resolution/adopt/${artifactId}/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function deferAutonomyAdvisory(artifactId: number, payload?: { actor?: string; rationale?: string; reason_codes?: string[] }) {
  return requestJson<{ resolution_id: number; resolution_status: string }>(`/api/autonomy-advisory-resolution/defer/${artifactId}/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function rejectAutonomyAdvisory(artifactId: number, payload?: { actor?: string; rationale?: string; reason_codes?: string[] }) {
  return requestJson<{ resolution_id: number; resolution_status: string }>(`/api/autonomy-advisory-resolution/reject/${artifactId}/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

import { requestJson } from './api/client';
import type {
  RecoveryCandidate,
  RecoveryRecommendation,
  RecoverySnapshot,
  RecoverySummary,
  RunRecoveryReviewResponse,
} from '../types/autonomyRecovery';

export function getAutonomyRecoveryCandidates() {
  return requestJson<RecoveryCandidate[]>('/api/autonomy-recovery/candidates/');
}

export function runAutonomyRecoveryReview(payload?: { actor?: string }) {
  return requestJson<RunRecoveryReviewResponse>('/api/autonomy-recovery/run-review/', {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function getAutonomyRecoverySnapshots() {
  return requestJson<RecoverySnapshot[]>('/api/autonomy-recovery/snapshots/');
}

export function getAutonomyRecoveryRecommendations() {
  return requestJson<RecoveryRecommendation[]>('/api/autonomy-recovery/recommendations/');
}

export function getAutonomyRecoverySummary() {
  return requestJson<RecoverySummary>('/api/autonomy-recovery/summary/');
}

export function requestResumeApproval(campaignId: number, payload?: { actor?: string }) {
  return requestJson<{ approval_request_id: number; status: string }>(`/api/autonomy-recovery/request-resume-approval/${campaignId}/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function requestCloseApproval(campaignId: number, payload?: { actor?: string }) {
  return requestJson<{ approval_request_id: number; status: string }>(`/api/autonomy-recovery/request-close-approval/${campaignId}/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

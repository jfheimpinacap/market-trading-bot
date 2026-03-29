import { requestJson } from './api/client';
import type {
  AutonomyCloseoutCandidate,
  CampaignCloseoutReport,
  CloseoutFinding,
  CloseoutRecommendation,
  CloseoutSummary,
  RunCloseoutReviewResponse,
} from '../types/autonomyCloseout';

export function getAutonomyCloseoutCandidates() {
  return requestJson<AutonomyCloseoutCandidate[]>('/api/autonomy-closeout/candidates/');
}

export function runAutonomyCloseoutReview(payload?: { actor?: string }) {
  return requestJson<RunCloseoutReviewResponse>('/api/autonomy-closeout/run-review/', {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function getAutonomyCloseoutReports() {
  return requestJson<CampaignCloseoutReport[]>('/api/autonomy-closeout/reports/');
}

export function getAutonomyCloseoutFindings() {
  return requestJson<CloseoutFinding[]>('/api/autonomy-closeout/findings/');
}

export function getAutonomyCloseoutRecommendations() {
  return requestJson<CloseoutRecommendation[]>('/api/autonomy-closeout/recommendations/');
}

export function getAutonomyCloseoutSummary() {
  return requestJson<CloseoutSummary>('/api/autonomy-closeout/summary/');
}

export function completeAutonomyCloseout(campaignId: number, payload?: { actor?: string }) {
  return requestJson<{ report_id: number; closeout_status: string }>(`/api/autonomy-closeout/complete/${campaignId}/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

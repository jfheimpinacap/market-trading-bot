import { requestJson } from './api/client';
import type {
  CampaignDisposition,
  CampaignDispositionCandidate,
  DispositionRecommendation,
  DispositionSummary,
  RunDispositionReviewResponse,
} from '../types/autonomyDisposition';

export function getAutonomyDispositionCandidates() {
  return requestJson<CampaignDispositionCandidate[]>('/api/autonomy-disposition/candidates/');
}

export function runAutonomyDispositionReview(payload?: { actor?: string }) {
  return requestJson<RunDispositionReviewResponse>('/api/autonomy-disposition/run-review/', {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function getAutonomyDispositionRecommendations() {
  return requestJson<DispositionRecommendation[]>('/api/autonomy-disposition/recommendations/');
}

export function getAutonomyDispositions() {
  return requestJson<CampaignDisposition[]>('/api/autonomy-disposition/dispositions/');
}

export function getAutonomyDispositionSummary() {
  return requestJson<DispositionSummary>('/api/autonomy-disposition/summary/');
}

export function requestAutonomyDispositionApproval(campaignId: number, payload?: { actor?: string }) {
  return requestJson<{ approval_request_id: number; status: string }>(`/api/autonomy-disposition/request-approval/${campaignId}/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function applyAutonomyDisposition(campaignId: number, payload?: { actor?: string }) {
  return requestJson<{ disposition_id: number; status: string; campaign_status: string }>(`/api/autonomy-disposition/apply/${campaignId}/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

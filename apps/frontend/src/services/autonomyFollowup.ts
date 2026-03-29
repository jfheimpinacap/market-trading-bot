import { requestJson } from './api/client';
import type {
  AutonomyFollowupCandidate,
  CampaignFollowup,
  FollowupRecommendation,
  FollowupSummary,
  RunFollowupReviewResponse,
} from '../types/autonomyFollowup';

export function getAutonomyFollowupCandidates() {
  return requestJson<AutonomyFollowupCandidate[]>('/api/autonomy-followup/candidates/');
}

export function runAutonomyFollowupReview(payload?: { actor?: string }) {
  return requestJson<RunFollowupReviewResponse>('/api/autonomy-followup/run-review/', {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function getAutonomyFollowups() {
  return requestJson<CampaignFollowup[]>('/api/autonomy-followup/followups/');
}

export function getAutonomyFollowupRecommendations() {
  return requestJson<FollowupRecommendation[]>('/api/autonomy-followup/recommendations/');
}

export function getAutonomyFollowupSummary() {
  return requestJson<FollowupSummary>('/api/autonomy-followup/summary/');
}

export function emitAutonomyFollowup(campaignId: number, payload?: { actor?: string }) {
  return requestJson<{ campaign: number; emitted_count: number }>(`/api/autonomy-followup/emit/${campaignId}/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

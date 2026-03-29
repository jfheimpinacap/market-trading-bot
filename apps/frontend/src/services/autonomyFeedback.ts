import { requestJson } from './api/client';
import type {
  AutonomyFeedbackCandidate,
  FeedbackRecommendation,
  FeedbackSummary,
  FollowupResolution,
  RunFeedbackReviewResponse,
} from '../types/autonomyFeedback';

export function getAutonomyFeedbackCandidates() {
  return requestJson<AutonomyFeedbackCandidate[]>('/api/autonomy-feedback/candidates/');
}

export function runAutonomyFeedbackReview(payload?: { actor?: string }) {
  return requestJson<RunFeedbackReviewResponse>('/api/autonomy-feedback/run-review/', {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function getAutonomyFeedbackResolutions() {
  return requestJson<FollowupResolution[]>('/api/autonomy-feedback/resolutions/');
}

export function getAutonomyFeedbackRecommendations() {
  return requestJson<FeedbackRecommendation[]>('/api/autonomy-feedback/recommendations/');
}

export function getAutonomyFeedbackSummary() {
  return requestJson<FeedbackSummary>('/api/autonomy-feedback/summary/');
}

export function completeAutonomyFeedbackResolution(followupId: number, payload?: { actor?: string }) {
  return requestJson<{ resolution_id: number; resolution_status: string }>(`/api/autonomy-feedback/complete/${followupId}/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

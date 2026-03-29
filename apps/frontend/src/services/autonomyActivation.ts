import { requestJson } from './api/client';
import type { ActivationCandidate, ActivationRecommendation, ActivationRunResponse, ActivationSummary, CampaignActivation } from '../types/autonomyActivation';

export function getAutonomyActivationCandidates() {
  return requestJson<ActivationCandidate[]>('/api/autonomy-activation/candidates/');
}

export function runAutonomyActivationDispatchReview(payload?: { actor?: string }) {
  return requestJson<ActivationRunResponse>('/api/autonomy-activation/run-dispatch-review/', {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function getAutonomyActivationRecommendations() {
  return requestJson<ActivationRecommendation[]>('/api/autonomy-activation/recommendations/');
}

export function getAutonomyActivations() {
  return requestJson<CampaignActivation[]>('/api/autonomy-activation/activations/');
}

export function getAutonomyActivationSummary() {
  return requestJson<ActivationSummary>('/api/autonomy-activation/summary/');
}

export function dispatchAutonomyCampaign(campaignId: number, payload?: { actor?: string; trigger_source?: 'manual_ui' | 'manual_api' | 'approval_resume'; rationale?: string }) {
  return requestJson<CampaignActivation>(`/api/autonomy-activation/dispatch/${campaignId}/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

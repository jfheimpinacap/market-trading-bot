import { requestJson } from './api/client';
import type {
  AutonomyInterventionSummary,
  CampaignInterventionAction,
  CampaignInterventionRequest,
  RunAutonomyInterventionReviewResponse,
} from '../types/autonomyInterventions';

export function getAutonomyInterventionRequests() {
  return requestJson<CampaignInterventionRequest[]>('/api/autonomy-interventions/requests/');
}

export function runAutonomyInterventionReview(payload?: { actor?: string }) {
  return requestJson<RunAutonomyInterventionReviewResponse>('/api/autonomy-interventions/run-review/', {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function getAutonomyInterventionSummary() {
  return requestJson<AutonomyInterventionSummary>('/api/autonomy-interventions/summary/');
}

export function createAutonomyInterventionRequest(campaignId: number, payload: Record<string, unknown>) {
  return requestJson<CampaignInterventionRequest>(`/api/autonomy-interventions/request/${campaignId}/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function executeAutonomyInterventionRequest(requestId: number, payload?: { actor?: string; rationale?: string; metadata?: Record<string, unknown> }) {
  return requestJson<CampaignInterventionAction>(`/api/autonomy-interventions/execute/${requestId}/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function getAutonomyInterventionActions() {
  return requestJson<CampaignInterventionAction[]>('/api/autonomy-interventions/actions/');
}

export function cancelAutonomyInterventionRequest(requestId: number) {
  return requestJson<CampaignInterventionRequest>(`/api/autonomy-interventions/cancel/${requestId}/`, {
    method: 'POST',
    body: JSON.stringify({}),
  });
}

import { requestJson } from './api/client';
import type { AutonomyInterventionSummary, CampaignInterventionAction, CampaignInterventionRequest } from '../types/autonomyInterventions';

export function getAutonomyInterventionRequests() {
  return requestJson<CampaignInterventionRequest[]>('/api/autonomy-interventions/requests/');
}

export function runAutonomyInterventionReview(payload?: { actor?: string }) {
  return requestJson<{ run: number; created_requests: number }>('/api/autonomy-interventions/run-review/', {
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

export function executeAutonomyInterventionRequest(requestId: number, payload?: { actor?: string }) {
  return requestJson<CampaignInterventionAction>(`/api/autonomy-interventions/execute/${requestId}/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function getAutonomyInterventionActions() {
  return requestJson<CampaignInterventionAction[]>('/api/autonomy-interventions/actions/');
}

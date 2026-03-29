import { requestJson } from './api/client';
<<<<<<< HEAD
import type {
  AutonomyInterventionSummary,
  CampaignInterventionAction,
  CampaignInterventionRequest,
  RunAutonomyInterventionReviewResponse,
} from '../types/autonomyInterventions';
=======
import type { AutonomyInterventionSummary, CampaignInterventionAction, CampaignInterventionRequest } from '../types/autonomyInterventions';
>>>>>>> origin/main

export function getAutonomyInterventionRequests() {
  return requestJson<CampaignInterventionRequest[]>('/api/autonomy-interventions/requests/');
}

export function runAutonomyInterventionReview(payload?: { actor?: string }) {
<<<<<<< HEAD
  return requestJson<RunAutonomyInterventionReviewResponse>('/api/autonomy-interventions/run-review/', {
=======
  return requestJson<{ run: number; created_requests: number }>('/api/autonomy-interventions/run-review/', {
>>>>>>> origin/main
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

<<<<<<< HEAD
export function executeAutonomyInterventionRequest(requestId: number, payload?: { actor?: string; rationale?: string; metadata?: Record<string, unknown> }) {
=======
export function executeAutonomyInterventionRequest(requestId: number, payload?: { actor?: string }) {
>>>>>>> origin/main
  return requestJson<CampaignInterventionAction>(`/api/autonomy-interventions/execute/${requestId}/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function getAutonomyInterventionActions() {
  return requestJson<CampaignInterventionAction[]>('/api/autonomy-interventions/actions/');
}
<<<<<<< HEAD

export function cancelAutonomyInterventionRequest(requestId: number) {
  return requestJson<CampaignInterventionRequest>(`/api/autonomy-interventions/cancel/${requestId}/`, {
    method: 'POST',
    body: JSON.stringify({}),
  });
}
=======
>>>>>>> origin/main

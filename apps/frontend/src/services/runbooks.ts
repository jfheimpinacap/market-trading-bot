import { requestJson } from './api/client';
import type { CreateRunbookPayload, RunbookInstance, RunbookRecommendation, RunbookSummary, RunbookTemplate } from '../types/runbooks';

export function getRunbookTemplates() {
  return requestJson<RunbookTemplate[]>('/api/runbooks/templates/');
}

export function getRunbooks(status?: string) {
  const suffix = status ? `?status=${encodeURIComponent(status)}` : '';
  return requestJson<RunbookInstance[]>(`/api/runbooks/${suffix}`);
}

export function getRunbook(id: number) {
  return requestJson<RunbookInstance>(`/api/runbooks/${id}/`);
}

export function createRunbook(payload: CreateRunbookPayload) {
  return requestJson<RunbookInstance>('/api/runbooks/create/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function runRunbookStep(runbookId: number, stepId: number) {
  return requestJson<{ step: number; status: string; runbook: RunbookInstance }>(`/api/runbooks/${runbookId}/run-step/${stepId}/`, {
    method: 'POST',
    body: '{}',
  });
}

export function completeRunbook(runbookId: number, note = '') {
  return requestJson<RunbookInstance>(`/api/runbooks/${runbookId}/complete/`, {
    method: 'POST',
    body: JSON.stringify({ note }),
  });
}

export function getRunbookSummary() {
  return requestJson<RunbookSummary>('/api/runbooks/summary/');
}

export function getRunbookRecommendations() {
  return requestJson<{ results: RunbookRecommendation[] }>('/api/runbooks/recommendations/');
}

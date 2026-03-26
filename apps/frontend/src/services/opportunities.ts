import { requestJson } from './api/client';
import type { OpportunityCycleItem, OpportunityCycleRun, OpportunitySummary } from '../types/opportunities';

export function runOpportunityCycle(payload?: { profile_slug?: string }) {
  return requestJson<OpportunityCycleRun>('/api/opportunities/run-cycle/', {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function getOpportunityCycles() {
  return requestJson<OpportunityCycleRun[]>('/api/opportunities/cycles/');
}

export function getOpportunityCycle(id: number | string) {
  return requestJson<OpportunityCycleRun>(`/api/opportunities/cycles/${id}/`);
}

export function getOpportunityItems(runId?: number) {
  const query = runId ? `?run_id=${runId}` : '';
  return requestJson<OpportunityCycleItem[]>(`/api/opportunities/items/${query}`);
}

export function getOpportunitySummary() {
  return requestJson<OpportunitySummary>('/api/opportunities/summary/');
}

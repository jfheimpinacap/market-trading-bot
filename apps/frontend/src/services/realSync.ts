import { requestJson } from './api/client';
import type { RealSyncRun, RealSyncStatusResponse, RealSyncSummary, RunRealSyncPayload } from '../types/realSync';

function buildQuery(params?: { provider?: string; limit?: number }) {
  const searchParams = new URLSearchParams();
  if (params?.provider) {
    searchParams.set('provider', params.provider);
  }
  if (params?.limit) {
    searchParams.set('limit', String(params.limit));
  }
  const query = searchParams.toString();
  return query ? `?${query}` : '';
}

export function runRealSync(payload: RunRealSyncPayload) {
  return requestJson<RealSyncRun>('/api/real-sync/run/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getRealSyncRuns(params?: { provider?: string; limit?: number }) {
  return requestJson<RealSyncRun[]>(`/api/real-sync/runs/${buildQuery(params)}`);
}

export function getRealSyncRun(id: number | string) {
  return requestJson<RealSyncRun>(`/api/real-sync/runs/${id}/`);
}

export function getRealSyncStatus() {
  return requestJson<RealSyncStatusResponse>('/api/real-sync/status/');
}

export function getRealSyncSummary() {
  return requestJson<RealSyncSummary>('/api/real-sync/summary/');
}

import { requestJson } from './api/client';
import type { ProvenanceSnapshot, TraceQueryResponse, TraceQueryRun, TraceRoot, TraceSummary } from '../types/trace';

export function runTraceQuery(payload: { root_type: string; root_id: string }) {
  return requestJson<TraceQueryResponse>('/api/trace/query/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getTraceRoot(id: number | string) {
  return requestJson<TraceRoot>(`/api/trace/roots/${id}/`);
}

export function getTraceSnapshot(rootType: string, rootId: string) {
  return requestJson<{ snapshot: ProvenanceSnapshot; partial: boolean }>(`/api/trace/snapshot/${rootType}/${rootId}/`);
}

export function getTraceQueryRuns() {
  return requestJson<TraceQueryRun[]>('/api/trace/query-runs/');
}

export function getTraceSummary() {
  return requestJson<TraceSummary>('/api/trace/summary/');
}

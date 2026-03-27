import { requestJson } from './api/client';
import type { MemoryDocument, MemoryRetrievalRun, MemoryRunResponse, MemorySummary, MemoryPrecedentSummary } from '../types/memory';

export function runMemoryIndex(payload?: { sources?: string[]; force_reembed?: boolean }) {
  return requestJson<{ indexed_by_source: Record<string, number>; documents_total: number; embeddings_generated: number; force_reembed: boolean }>('/memory/index/', {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function runMemoryRetrieval(payload: { query_text: string; query_type?: string; context_metadata?: Record<string, unknown>; limit?: number; min_similarity?: number }) {
  return requestJson<MemoryRunResponse>('/memory/retrieve/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getMemoryDocuments() {
  return requestJson<MemoryDocument[]>('/memory/documents/');
}

export function getMemoryRetrievalRuns() {
  return requestJson<MemoryRetrievalRun[]>('/memory/retrieval-runs/');
}

export function getMemoryRetrievalRun(id: number) {
  return requestJson<MemoryRetrievalRun>(`/memory/retrieval-runs/${id}/`);
}

export function getMemorySummary() {
  return requestJson<MemorySummary>('/memory/summary/');
}

export function getMemoryPrecedentSummary(runId?: number) {
  return requestJson<MemoryPrecedentSummary>(`/memory/precedent-summary/${runId ? `?run_id=${runId}` : ''}`);
}

import { requestJson } from './api/client';
import type {
  AgentPrecedentUse,
  MemoryDocument,
  MemoryInfluenceSummary,
  MemoryPrecedentSummary,
  MemoryRetrievalRun,
  MemoryRunResponse,
  MemorySummary,
} from '../types/memory';

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

export function getAgentPrecedentUses(agentName?: string) {
  const qs = agentName ? `?agent_name=${agentName}` : '';
  return requestJson<AgentPrecedentUse[]>(`/memory/precedent-uses/${qs}`);
}

export function getAgentPrecedentUse(id: number) {
  return requestJson<AgentPrecedentUse>(`/memory/precedent-uses/${id}/`);
}

export function getMemoryInfluenceSummary(queryText?: string, queryType = 'manual') {
  const qs = queryText ? `?query_text=${encodeURIComponent(queryText)}&query_type=${encodeURIComponent(queryType)}` : '';
  return requestJson<MemoryInfluenceSummary>(`/memory/influence-summary/${qs}`);
}

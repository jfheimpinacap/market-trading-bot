import { requestJson } from './api/client';
import type { NarrativeItem, ResearchCandidate, ResearchScanRun, ResearchSource, ResearchSummary } from '../types/research';

export function getResearchSources() {
  return requestJson<ResearchSource[]>('/api/research/sources/');
}

export function createResearchSource(payload: Partial<ResearchSource>) {
  return requestJson<ResearchSource>('/api/research/sources/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function runResearchIngest(payload: { source_ids?: number[]; run_analysis?: boolean } = {}) {
  return requestJson<ResearchScanRun>('/api/research/run-ingest/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function runResearchFullScan(payload: { source_ids?: number[] } = {}) {
  return requestJson<ResearchScanRun>('/api/research/run-full-scan/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function runResearchAnalysis() {
  return requestJson<{ analyzed: number; errors: string[] }>('/api/research/run-analysis/', {
    method: 'POST',
    body: JSON.stringify({}),
  });
}

export function getResearchItems() {
  return requestJson<NarrativeItem[]>('/api/research/items/');
}

export function getResearchItem(id: number | string) {
  return requestJson<NarrativeItem>(`/api/research/items/${id}/`);
}

export function getResearchCandidates() {
  return requestJson<ResearchCandidate[]>('/api/research/candidates/');
}

export function getResearchSummary() {
  return requestJson<ResearchSummary>('/api/research/summary/');
}

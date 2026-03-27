import { requestJson } from './api/client';
import type {
  MarketUniverseScanRun,
  NarrativeItem,
  PursuitCandidate,
  ResearchBoardSummary,
  ResearchCandidate,
  ResearchScanRun,
  ResearchSource,
  ResearchSummary,
} from '../types/research';

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

export function runUniverseScan(payload: { filter_profile?: string; provider_scope?: string[]; source_scope?: string[] } = {}) {
  return requestJson<MarketUniverseScanRun>('/api/research/run-universe-scan/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getUniverseScans() {
  return requestJson<MarketUniverseScanRun[]>('/api/research/universe-scans/');
}

export function getUniverseScan(id: number | string) {
  return requestJson<MarketUniverseScanRun>(`/api/research/universe-scans/${id}/`);
}

export function getPursuitCandidates(status?: 'shortlisted' | 'watch' | 'filtered_out') {
  const query = status ? `?status=${status}` : '';
  return requestJson<PursuitCandidate[]>(`/api/research/pursuit-candidates/${query}`);
}

export function getResearchBoardSummary() {
  return requestJson<ResearchBoardSummary>('/api/research/board-summary/');
}

export function runTriageToPrediction(payload: { run_id: number; limit?: number }) {
  return requestJson<{ pipeline_run_id: number; pipeline_status: string; pipeline_summary: string }>(
    '/api/research/run-triage-to-prediction/',
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
  );
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

export function runResearchPrecedentAssist(payload: { query_text: string; market_id?: number; limit?: number }) {
  return requestJson<{
    retrieval_run_id: number;
    result_count: number;
    influence_mode: string;
    precedent_confidence: number;
    summary: Record<string, unknown>;
  }>('/api/research/precedent-assist/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

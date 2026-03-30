import { requestJson } from './api/client';
import type { NarrativeCluster, NarrativeSignal, ScanRecommendation, ScanSummary, SourceScanRun } from '../types/scanAgent';

export function runScanAgent(payload: { source_ids?: number[] } = {}) {
  return requestJson<SourceScanRun>('/api/scan-agent/run-scan/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getScanSignals(params?: { status?: string }) {
  const query = params?.status ? `?status=${encodeURIComponent(params.status)}` : '';
  return requestJson<NarrativeSignal[]>(`/api/scan-agent/signals/${query}`);
}

export function getScanClusters(params?: { cluster_status?: string }) {
  const query = params?.cluster_status ? `?cluster_status=${encodeURIComponent(params.cluster_status)}` : '';
  return requestJson<NarrativeCluster[]>(`/api/scan-agent/clusters/${query}`);
}

export function getScanRecommendations(params?: { recommendation_type?: string }) {
  const query = params?.recommendation_type ? `?recommendation_type=${encodeURIComponent(params.recommendation_type)}` : '';
  return requestJson<ScanRecommendation[]>(`/api/scan-agent/recommendations/${query}`);
}

export function getScanSummary() {
  return requestJson<ScanSummary>('/api/scan-agent/summary/');
}

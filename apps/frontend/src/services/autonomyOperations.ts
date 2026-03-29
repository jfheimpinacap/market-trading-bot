import { requestJson } from './api/client';
import type {
  AutonomyOperationsSummary,
  CampaignAttentionSignal,
  CampaignRuntimeSnapshot,
  OperationsRecommendation,
  RunAutonomyOperationsMonitorResponse,
} from '../types/autonomyOperations';

export function getAutonomyOperationsRuntime() {
  return requestJson<CampaignRuntimeSnapshot[]>('/api/autonomy-operations/runtime/');
}

export function runAutonomyOperationsMonitor(payload?: { actor?: string }) {
  return requestJson<RunAutonomyOperationsMonitorResponse>('/api/autonomy-operations/run-monitor/', {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function getAutonomyOperationsSignals() {
  return requestJson<CampaignAttentionSignal[]>('/api/autonomy-operations/signals/');
}

export function getAutonomyOperationsRecommendations() {
  return requestJson<OperationsRecommendation[]>('/api/autonomy-operations/recommendations/');
}

export function getAutonomyOperationsSummary() {
  return requestJson<AutonomyOperationsSummary>('/api/autonomy-operations/summary/');
}

export function acknowledgeAutonomySignal(signalId: number, payload?: { actor?: string }) {
  return requestJson<CampaignAttentionSignal>(`/api/autonomy-operations/signals/${signalId}/acknowledge/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

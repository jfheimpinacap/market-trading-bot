import { requestJson } from './api/client';
import type {
  AdapterQualificationRun,
  AdapterReadinessRecommendation,
  ConnectorCasesResponse,
  ConnectorSummary,
} from '../types/connectors';

export function getConnectorCases() {
  return requestJson<ConnectorCasesResponse>('/api/connectors/cases/');
}

export function runConnectorQualification(payload?: { fixture_profile?: string; metadata?: Record<string, unknown> }) {
  return requestJson<AdapterQualificationRun>('/api/connectors/run-qualification/', {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function getConnectorRuns() {
  return requestJson<AdapterQualificationRun[]>('/api/connectors/runs/');
}

export function getConnectorRun(id: number | string) {
  return requestJson<AdapterQualificationRun>(`/api/connectors/runs/${id}/`);
}

export function getCurrentConnectorReadiness() {
  return requestJson<AdapterReadinessRecommendation | { detail: string }>('/api/connectors/current-readiness/');
}

export function getConnectorSummary() {
  return requestJson<ConnectorSummary>('/api/connectors/summary/');
}

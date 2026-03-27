import { requestJson } from './api/client';
import type { IncidentCurrentState, IncidentRecord, IncidentSummary } from '../types/incidents';

export function getIncidents(status?: string) {
  const suffix = status ? `?status=${encodeURIComponent(status)}` : '';
  return requestJson<IncidentRecord[]>(`/api/incidents/${suffix}`);
}

export function getIncident(id: number) {
  return requestJson<IncidentRecord>(`/api/incidents/${id}/`);
}

export function getIncidentCurrentState() {
  return requestJson<IncidentCurrentState>('/api/incidents/current-state/');
}

export function runIncidentDetection() {
  return requestJson<{ detected_count: number; incident_ids: number[] }>('/api/incidents/run-detection/', {
    method: 'POST',
    body: '{}',
  });
}

export function mitigateIncident(id: number) {
  return requestJson<IncidentRecord>(`/api/incidents/${id}/mitigate/`, {
    method: 'POST',
    body: '{}',
  });
}

export function resolveIncident(id: number, note = '') {
  return requestJson<IncidentRecord>(`/api/incidents/${id}/resolve/`, {
    method: 'POST',
    body: JSON.stringify({ note }),
  });
}

export function getIncidentSummary() {
  return requestJson<IncidentSummary>('/api/incidents/summary/');
}

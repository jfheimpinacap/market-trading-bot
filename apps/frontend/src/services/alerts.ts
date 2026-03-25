import { requestJson } from './api/client';
import type { OperatorAlert, OperatorAlertsSummary, OperatorDigest } from '../types/alerts';

export type AlertsFilters = {
  status?: string;
  severity?: string;
  source?: string;
  alert_type?: string;
};

function toQueryString(filters?: AlertsFilters) {
  if (!filters) return '';
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') params.set(key, String(value));
  });
  const query = params.toString();
  return query ? `?${query}` : '';
}

export function getAlerts(filters?: AlertsFilters) {
  return requestJson<OperatorAlert[]>(`/api/alerts/${toQueryString(filters)}`);
}

export function getAlert(id: string | number) {
  return requestJson<OperatorAlert>(`/api/alerts/${id}/`);
}

export function getAlertsSummary() {
  return requestJson<OperatorAlertsSummary>('/api/alerts/summary/');
}

export function acknowledgeAlert(id: string | number) {
  return requestJson<OperatorAlert>(`/api/alerts/${id}/acknowledge/`, { method: 'POST', body: JSON.stringify({}) });
}

export function resolveAlert(id: string | number) {
  return requestJson<OperatorAlert>(`/api/alerts/${id}/resolve/`, { method: 'POST', body: JSON.stringify({}) });
}

export function getAlertDigests() {
  return requestJson<OperatorDigest[]>('/api/alerts/digests/');
}

export function getAlertDigest(id: string | number) {
  return requestJson<OperatorDigest>(`/api/alerts/digests/${id}/`);
}

export function buildAlertDigest(digestType: 'daily' | 'session' | 'manual' | 'cycle_window' = 'manual') {
  return requestJson<OperatorDigest>('/api/alerts/build-digest/', {
    method: 'POST',
    body: JSON.stringify({ digest_type: digestType }),
  });
}

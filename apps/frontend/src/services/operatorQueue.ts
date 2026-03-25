import { requestJson } from './api/client';
import type { OperatorQueueItem, OperatorQueueSummary } from '../types/operatorQueue';

export type OperatorQueueFilters = {
  status?: string;
  source?: string;
  queue_type?: string;
  priority?: string;
  source_type?: string;
  is_real_data?: boolean;
};

function toQueryString(filters?: OperatorQueueFilters) {
  if (!filters) return '';
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      params.set(key, String(value));
    }
  });
  const query = params.toString();
  return query ? `?${query}` : '';
}

export function getOperatorQueueItems(filters?: OperatorQueueFilters) {
  return requestJson<OperatorQueueItem[]>(`/api/operator-queue/${toQueryString(filters)}`);
}

export function getOperatorQueueItem(id: string | number) {
  return requestJson<OperatorQueueItem>(`/api/operator-queue/${id}/`);
}

export function getOperatorQueueSummary() {
  return requestJson<OperatorQueueSummary>('/api/operator-queue/summary/');
}

export function approveOperatorQueueItem(id: string | number, decisionNote = '') {
  return requestJson<OperatorQueueItem>(`/api/operator-queue/${id}/approve/`, {
    method: 'POST',
    body: JSON.stringify({ decision_note: decisionNote }),
  });
}

export function rejectOperatorQueueItem(id: string | number, decisionNote = '') {
  return requestJson<OperatorQueueItem>(`/api/operator-queue/${id}/reject/`, {
    method: 'POST',
    body: JSON.stringify({ decision_note: decisionNote }),
  });
}

export function snoozeOperatorQueueItem(id: string | number, payload: { decision_note?: string; snooze_hours?: number; snooze_until?: string } = {}) {
  return requestJson<OperatorQueueItem>(`/api/operator-queue/${id}/snooze/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

import { requestJson } from './api/client';
import type { MarketSignal, MockAgent, SignalQueryParams, SignalSummary } from '../types/signals';

function buildQueryString(params?: SignalQueryParams) {
  if (!params) {
    return '';
  }

  const searchParams = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null) {
      return;
    }

    const normalized = `${value}`.trim();
    if (!normalized) {
      return;
    }

    searchParams.set(key, normalized);
  });

  const queryString = searchParams.toString();
  return queryString ? `?${queryString}` : '';
}

export function getSignals(params?: SignalQueryParams) {
  return requestJson<MarketSignal[]>(`/api/signals/${buildQueryString(params)}`);
}

export function getSignal(id: string | number) {
  return requestJson<MarketSignal>(`/api/signals/${id}/`);
}

export function getSignalAgents() {
  return requestJson<MockAgent[]>('/api/signals/agents/');
}

export function getSignalsSummary() {
  return requestJson<SignalSummary>('/api/signals/summary/');
}

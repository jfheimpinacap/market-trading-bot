import { requestJson } from './api/client';
import type {
  MarketDetail,
  MarketEvent,
  MarketProvider,
  MarketQueryParams,
  MarketSystemSummary,
  MarketListItem,
} from '../types/markets';

function buildQueryString(params?: MarketQueryParams) {
  if (!params) {
    return '';
  }

  const searchParams = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null) {
      return;
    }

    const normalized = `${value}`.trim();
    if (normalized.length === 0) {
      return;
    }

    searchParams.set(key, normalized);
  });

  const queryString = searchParams.toString();
  return queryString ? `?${queryString}` : '';
}

export function getMarketSystemSummary() {
  return requestJson<MarketSystemSummary>('/api/markets/system-summary/');
}

export function getProviders() {
  return requestJson<MarketProvider[]>('/api/markets/providers/');
}

export function getEvents(params?: Pick<MarketQueryParams, 'provider' | 'category' | 'status'>) {
  return requestJson<MarketEvent[]>(`/api/markets/events/${buildQueryString(params)}`);
}

export function getMarkets(params?: MarketQueryParams) {
  return requestJson<MarketListItem[]>(`/api/markets/${buildQueryString(params)}`);
}

export function getMarketDetail(id: string | number) {
  return requestJson<MarketDetail>(`/api/markets/${id}/`);
}

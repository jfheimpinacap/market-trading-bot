import { requestJson } from './api/client';
import type {
  MarketSignal,
  MockAgent,
  OpportunitySignal,
  SignalBoardSummary,
  SignalFusionRun,
  SignalProfileSlug,
  SignalQueryParams,
  SignalSummary,
} from '../types/signals';

function buildQueryString(params?: Record<string, string | number | undefined>) {
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

export function runSignalFusion(payload?: { profile_slug?: SignalProfileSlug; market_ids?: number[] }) {
  return requestJson<SignalFusionRun>('/api/signals/run-fusion/', {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function getSignalRuns() {
  return requestJson<SignalFusionRun[]>('/api/signals/runs/');
}

export function getSignalRun(id: string | number) {
  return requestJson<SignalFusionRun>(`/api/signals/runs/${id}/`);
}

export function getOpportunitySignals(params?: { run_id?: string | number; status?: string }) {
  return requestJson<OpportunitySignal[]>(`/api/signals/opportunities/${buildQueryString(params)}`);
}

export function getSignalBoardSummary() {
  return requestJson<SignalBoardSummary>('/api/signals/board-summary/');
}

export function runFusionToProposal(payload: { run_id: number; min_priority?: number }) {
  return requestJson<{ run_id: number; proposals_created: number }>('/api/signals/run-to-proposal/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

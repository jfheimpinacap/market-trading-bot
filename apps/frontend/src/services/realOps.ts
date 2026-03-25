import { requestJson } from './api/client';
import type { RealMarketOpRun, RealMarketOpsEvaluateResponse, RealMarketOpsStatus } from '../types/realOps';

export function evaluateRealMarketOps(triggered_from: 'manual' | 'automation' = 'manual') {
  return requestJson<RealMarketOpsEvaluateResponse>('/api/real-ops/evaluate/', {
    method: 'POST',
    body: JSON.stringify({ triggered_from }),
  });
}

export function runRealMarketOps(triggered_from: 'manual' | 'automation' | 'continuous_demo' = 'manual') {
  return requestJson<RealMarketOpRun>('/api/real-ops/run/', {
    method: 'POST',
    body: JSON.stringify({ triggered_from }),
  });
}

export function getRealMarketOpRuns(limit = 20) {
  return requestJson<RealMarketOpRun[]>(`/api/real-ops/runs/?limit=${limit}`);
}

export function getRealMarketOpRun(id: string | number) {
  return requestJson<RealMarketOpRun>(`/api/real-ops/runs/${id}/`);
}

export function getRealMarketOpStatus() {
  return requestJson<RealMarketOpsStatus>('/api/real-ops/status/');
}

export function getEligibleRealMarkets() {
  return requestJson<Pick<RealMarketOpsEvaluateResponse, 'eligible_markets' | 'excluded_markets'>>('/api/real-ops/eligible-markets/');
}

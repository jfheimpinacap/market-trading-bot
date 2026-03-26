import { requestJson } from './api/client';
import type { PortfolioExposureSnapshot, PortfolioGovernanceRun, PortfolioGovernanceSummary, PortfolioThrottleDecision } from '../types/portfolioGovernor';

export function runPortfolioGovernance(payload: Record<string, unknown> = {}) {
  return requestJson<PortfolioGovernanceRun>('/api/portfolio-governor/run-governance/', { method: 'POST', body: JSON.stringify(payload) });
}

export function getPortfolioGovernanceRuns() {
  return requestJson<PortfolioGovernanceRun[]>('/api/portfolio-governor/runs/');
}

export function getPortfolioGovernanceRun(id: number | string) {
  return requestJson<PortfolioGovernanceRun>(`/api/portfolio-governor/runs/${id}/`);
}

export function getPortfolioExposure() {
  return requestJson<PortfolioExposureSnapshot>('/api/portfolio-governor/exposure/');
}

export function getPortfolioThrottle() {
  return requestJson<PortfolioThrottleDecision>('/api/portfolio-governor/throttle/');
}

export function getPortfolioGovernanceSummary() {
  return requestJson<PortfolioGovernanceSummary>('/api/portfolio-governor/summary/');
}

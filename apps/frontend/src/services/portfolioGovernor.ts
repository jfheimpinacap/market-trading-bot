import { requestJson } from './api/client';
import type {
  PortfolioExposureClusterSnapshot,
  PortfolioExposureConflictReview,
  PortfolioExposureCoordinationRun,
  PortfolioExposureCoordinationSummary,
  PortfolioExposureDecision,
  PortfolioExposureRecommendation,
  PortfolioExposureSnapshot,
  PortfolioGovernanceRun,
  PortfolioGovernanceSummary,
  PortfolioThrottleDecision,
  SessionExposureContribution,
} from '../types/portfolioGovernor';

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

export function runExposureCoordinationReview() {
  return requestJson<PortfolioExposureCoordinationRun>('/api/portfolio-governor/run-exposure-coordination-review/', { method: 'POST' });
}

export function getExposureCoordinationRuns() {
  return requestJson<PortfolioExposureCoordinationRun[]>('/api/portfolio-governor/exposure-coordination-runs/');
}

export function getExposureClusterSnapshots() {
  return requestJson<PortfolioExposureClusterSnapshot[]>('/api/portfolio-governor/exposure-cluster-snapshots/');
}

export function getSessionExposureContributions() {
  return requestJson<SessionExposureContribution[]>('/api/portfolio-governor/session-exposure-contributions/');
}

export function getExposureConflictReviews() {
  return requestJson<PortfolioExposureConflictReview[]>('/api/portfolio-governor/exposure-conflict-reviews/');
}

export function getExposureDecisions() {
  return requestJson<PortfolioExposureDecision[]>('/api/portfolio-governor/exposure-decisions/');
}

export function getExposureRecommendations() {
  return requestJson<PortfolioExposureRecommendation[]>('/api/portfolio-governor/exposure-recommendations/');
}

export function getExposureCoordinationSummary() {
  return requestJson<PortfolioExposureCoordinationSummary>('/api/portfolio-governor/exposure-coordination-summary/');
}

import { requestJson } from './api/client';
import type {
  PortfolioExposureApplyDecision,
  PortfolioExposureApplyRecommendation,
  PortfolioExposureApplyRecord,
  PortfolioExposureApplyRun,
  PortfolioExposureApplySummary,
  PortfolioExposureApplyTarget,
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

export function applyExposureDecision(decisionId: number, payload: Record<string, unknown> = {}) {
  return requestJson<PortfolioExposureApplyRun>(`/api/portfolio-governor/apply-exposure-decision/${decisionId}/`, { method: 'POST', body: JSON.stringify(payload) });
}

export function runExposureApplyReview(payload: Record<string, unknown> = {}) {
  return requestJson<PortfolioExposureApplyRun>('/api/portfolio-governor/run-exposure-apply-review/', { method: 'POST', body: JSON.stringify(payload) });
}

export function getExposureCoordinationRuns() {
  return requestJson<PortfolioExposureCoordinationRun[]>('/api/portfolio-governor/exposure-coordination-runs/');
}

export function getExposureApplyRuns() {
  return requestJson<PortfolioExposureApplyRun[]>('/api/portfolio-governor/exposure-apply-runs/');
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

export function getExposureApplyTargets() {
  return requestJson<PortfolioExposureApplyTarget[]>('/api/portfolio-governor/exposure-apply-targets/');
}

export function getExposureApplyDecisions() {
  return requestJson<PortfolioExposureApplyDecision[]>('/api/portfolio-governor/exposure-apply-decisions/');
}

export function getExposureApplyRecords() {
  return requestJson<PortfolioExposureApplyRecord[]>('/api/portfolio-governor/exposure-apply-records/');
}

export function getExposureApplyRecommendations() {
  return requestJson<PortfolioExposureApplyRecommendation[]>('/api/portfolio-governor/exposure-apply-recommendations/');
}

export function getExposureCoordinationSummary() {
  return requestJson<PortfolioExposureCoordinationSummary>('/api/portfolio-governor/exposure-coordination-summary/');
}

export function getExposureApplySummary() {
  return requestJson<PortfolioExposureApplySummary>('/api/portfolio-governor/exposure-apply-summary/');
}

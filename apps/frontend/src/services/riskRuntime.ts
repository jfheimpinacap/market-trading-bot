import { requestJson } from './api/client';
import type {
  PositionWatchPlan,
  AutonomousExecutionReadiness,
  RiskApprovalDecision,
  RiskRuntimeCandidate,
  RiskRuntimeRecommendation,
  RiskRuntimeRun,
  RiskRuntimeSummary,
  RiskSizingPlan,
} from '../types/riskAgent';

export function runRiskRuntimeReview(payload?: { triggered_by?: string }) {
  return requestJson<RiskRuntimeRun>('/api/risk-agent/run-intake-review/', {
    method: 'POST',
    body: JSON.stringify(payload ?? { triggered_by: 'manual_ui' }),
  });
}

export function getRiskRuntimeCandidates(params?: { run_id?: number; provider?: string; category?: string }) {
  const query = new URLSearchParams();
  if (params?.run_id) query.set('run_id', String(params.run_id));
  if (params?.provider) query.set('provider', params.provider);
  if (params?.category) query.set('category', params.category);
  return requestJson<RiskRuntimeCandidate[]>(`/api/risk-agent/intake-candidates/${query.toString() ? `?${query}` : ''}`);
}

export function getRiskApprovalDecisions(params?: { run_id?: number; status?: string }) {
  const query = new URLSearchParams();
  if (params?.run_id) query.set('run_id', String(params.run_id));
  if (params?.status) query.set('status', params.status);
  return requestJson<RiskApprovalDecision[]>(`/api/risk-agent/approval-reviews/${query.toString() ? `?${query}` : ''}`);
}

export function getRiskSizingPlans(params?: { run_id?: number }) {
  const query = new URLSearchParams();
  if (params?.run_id) query.set('run_id', String(params.run_id));
  return requestJson<RiskSizingPlan[]>(`/api/risk-agent/sizing-plans/${query.toString() ? `?${query}` : ''}`);
}

export function getRiskWatchPlans(params?: { run_id?: number }) {
  const query = new URLSearchParams();
  if (params?.run_id) query.set('run_id', String(params.run_id));
  return requestJson<PositionWatchPlan[]>(`/api/risk-agent/watch-plans/${query.toString() ? `?${query}` : ''}`);
}

export function getRiskRuntimeRecommendations(params?: { run_id?: number; recommendation_type?: string }) {
  const query = new URLSearchParams();
  if (params?.run_id) query.set('run_id', String(params.run_id));
  if (params?.recommendation_type) query.set('recommendation_type', params.recommendation_type);
  return requestJson<RiskRuntimeRecommendation[]>(`/api/risk-agent/intake-recommendations/${query.toString() ? `?${query}` : ''}`);
}

export function getAutonomousExecutionReadiness(params?: { run_id?: number }) {
  const query = new URLSearchParams();
  if (params?.run_id) query.set('run_id', String(params.run_id));
  return requestJson<AutonomousExecutionReadiness[]>(`/api/risk-agent/execution-readiness/${query.toString() ? `?${query}` : ''}`);
}

export function getRiskRuntimeSummary() {
  return requestJson<RiskRuntimeSummary>('/api/risk-agent/intake-summary/');
}

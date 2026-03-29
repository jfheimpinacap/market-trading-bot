import { requestJson } from './api/client';
import type { AutonomyDecisionCandidate, AutonomyDecisionSummary, DecisionRecommendation, GovernanceDecision } from '../types/autonomyDecision';

export function getAutonomyDecisionCandidates() {
  return requestJson<AutonomyDecisionCandidate[]>('/api/autonomy-decision/candidates/');
}

export function runAutonomyDecisionReview(payload?: { actor?: string }) {
  return requestJson<{ run: number; candidate_count: number; recommendation_count: number }>('/api/autonomy-decision/run-review/', {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function getAutonomyDecisions() {
  return requestJson<GovernanceDecision[]>('/api/autonomy-decision/decisions/');
}

export function getAutonomyDecisionRecommendations() {
  return requestJson<DecisionRecommendation[]>('/api/autonomy-decision/recommendations/');
}

export function getAutonomyDecisionSummary() {
  return requestJson<AutonomyDecisionSummary>('/api/autonomy-decision/summary/');
}

export function registerAutonomyDecision(proposalId: number, payload?: { actor?: string }) {
  return requestJson<{ decision_id: number; decision_status: string }>(`/api/autonomy-decision/register/${proposalId}/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function acknowledgeAutonomyDecision(decisionId: number) {
  return requestJson<{ decision_id: number; decision_status: string }>(`/api/autonomy-decision/acknowledge/${decisionId}/`, {
    method: 'POST',
    body: JSON.stringify({}),
  });
}

import { requestJson } from './api/client';
import type {
  AutonomyIntakeCandidate,
  AutonomyIntakeSummary,
  IntakeRecommendation,
  PlanningProposal,
  RunAutonomyIntakeReviewResponse,
} from '../types/autonomyIntake';

export function getAutonomyIntakeCandidates() {
  return requestJson<AutonomyIntakeCandidate[]>('/api/autonomy-intake/candidates/');
}

export function runAutonomyIntakeReview(payload?: { actor?: string }) {
  return requestJson<RunAutonomyIntakeReviewResponse>('/api/autonomy-intake/run-review/', {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function getAutonomyIntakeProposals() {
  return requestJson<PlanningProposal[]>('/api/autonomy-intake/proposals/');
}

export function getAutonomyIntakeRecommendations() {
  return requestJson<IntakeRecommendation[]>('/api/autonomy-intake/recommendations/');
}

export function getAutonomyIntakeSummary() {
  return requestJson<AutonomyIntakeSummary>('/api/autonomy-intake/summary/');
}

export function emitAutonomyIntakeProposal(backlogItemId: number, payload?: { actor?: string }) {
  return requestJson<{ proposal_id: number; proposal_status: string }>(`/api/autonomy-intake/emit/${backlogItemId}/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function acknowledgeAutonomyIntakeProposal(proposalId: number, payload?: { actor?: string }) {
  return requestJson<{ proposal_id: number; proposal_status: string }>(`/api/autonomy-intake/acknowledge/${proposalId}/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

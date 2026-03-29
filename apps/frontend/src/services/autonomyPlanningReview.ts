import { requestJson } from './api/client';
import type {
  AutonomyPlanningReviewCandidate,
  AutonomyPlanningReviewSummary,
  PlanningProposalResolution,
  PlanningReviewRecommendation,
  RunAutonomyPlanningReviewResponse,
} from '../types/autonomyPlanningReview';

export function getAutonomyPlanningReviewCandidates() {
  return requestJson<AutonomyPlanningReviewCandidate[]>('/api/autonomy-planning-review/candidates/');
}

export function runAutonomyPlanningReview(payload?: { actor?: string }) {
  return requestJson<RunAutonomyPlanningReviewResponse>('/api/autonomy-planning-review/run-review/', {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function getAutonomyPlanningReviewResolutions() {
  return requestJson<PlanningProposalResolution[]>('/api/autonomy-planning-review/resolutions/');
}

export function getAutonomyPlanningReviewRecommendations() {
  return requestJson<PlanningReviewRecommendation[]>('/api/autonomy-planning-review/recommendations/');
}

export function getAutonomyPlanningReviewSummary() {
  return requestJson<AutonomyPlanningReviewSummary>('/api/autonomy-planning-review/summary/');
}

export function acknowledgeAutonomyPlanningProposal(proposalId: number, payload?: { actor?: string }) {
  return requestJson<{ resolution_id: number; resolution_status: string }>(`/api/autonomy-planning-review/acknowledge/${proposalId}/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function acceptAutonomyPlanningProposal(proposalId: number, payload?: { actor?: string; rationale?: string; reason_codes?: string[] }) {
  return requestJson<{ resolution_id: number; resolution_status: string }>(`/api/autonomy-planning-review/accept/${proposalId}/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function deferAutonomyPlanningProposal(proposalId: number, payload?: { actor?: string; rationale?: string; reason_codes?: string[] }) {
  return requestJson<{ resolution_id: number; resolution_status: string }>(`/api/autonomy-planning-review/defer/${proposalId}/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function rejectAutonomyPlanningProposal(proposalId: number, payload?: { actor?: string; rationale?: string; reason_codes?: string[] }) {
  return requestJson<{ resolution_id: number; resolution_status: string }>(`/api/autonomy-planning-review/reject/${proposalId}/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

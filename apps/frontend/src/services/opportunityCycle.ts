import { requestJson } from './api/client';
import type {
  OpportunityCycleSummary,
  OpportunityFusionAssessment,
  OpportunityFusionCandidate,
  OpportunityRecommendation,
  PaperOpportunityProposal,
} from '../types/opportunityCycle';

export function runOpportunityCycleReview() {
  return requestJson<OpportunityCycleSummary>('/api/opportunity-cycle/run-review/', {
    method: 'POST',
    body: JSON.stringify({}),
  });
}

export function getOpportunityCycleCandidates() {
  return requestJson<OpportunityFusionCandidate[]>('/api/opportunity-cycle/candidates/');
}

export function getOpportunityCycleAssessments() {
  return requestJson<OpportunityFusionAssessment[]>('/api/opportunity-cycle/assessments/');
}

export function getOpportunityCycleProposals() {
  return requestJson<PaperOpportunityProposal[]>('/api/opportunity-cycle/proposals/');
}

export function getOpportunityCycleRecommendations() {
  return requestJson<OpportunityRecommendation[]>('/api/opportunity-cycle/recommendations/');
}

export function getOpportunityCycleSummary() {
  return requestJson<OpportunityCycleSummary>('/api/opportunity-cycle/summary/');
}

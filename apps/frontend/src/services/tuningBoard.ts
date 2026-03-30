import { requestJson } from './api/client';
import type { TuningBundle, TuningImpactHypothesis, TuningProposal, TuningRecommendation, TuningReviewRun, TuningSummary } from '../types/tuningBoard';

export function runTuningReview(payload?: { evaluation_run_id?: number; metadata?: Record<string, unknown> }) {
  return requestJson<TuningReviewRun>('/api/tuning/run-review/', {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function getTuningProposals(params?: { target_component?: string; target_scope?: string; priority_level?: string; proposal_status?: string }) {
  const query = new URLSearchParams();
  if (params?.target_component) query.set('target_component', params.target_component);
  if (params?.target_scope) query.set('target_scope', params.target_scope);
  if (params?.priority_level) query.set('priority_level', params.priority_level);
  if (params?.proposal_status) query.set('proposal_status', params.proposal_status);
  return requestJson<TuningProposal[]>(`/api/tuning/proposals/${query.toString() ? `?${query.toString()}` : ''}`);
}

export function getTuningHypotheses() {
  return requestJson<TuningImpactHypothesis[]>('/api/tuning/hypotheses/');
}

export function getTuningRecommendations() {
  return requestJson<TuningRecommendation[]>('/api/tuning/recommendations/');
}

export function getTuningSummary() {
  return requestJson<TuningSummary>('/api/tuning/summary/');
}

export function getTuningBundles() {
  return requestJson<TuningBundle[]>('/api/tuning/bundles/');
}

import { requestJson } from './api/client';
import type { PolicyTuningApplicationLog, PolicyTuningCandidate, PolicyTuningReviewDecision, PolicyTuningSummary } from '../types/policyTuning';

export function createPolicyTuningCandidate(payload: { recommendation_id: number; status?: 'DRAFT' | 'PENDING_APPROVAL' }) {
  return requestJson<PolicyTuningCandidate>('/api/policy-tuning/create-candidate/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getPolicyTuningCandidates() {
  return requestJson<PolicyTuningCandidate[]>('/api/policy-tuning/candidates/');
}

export function getPolicyTuningCandidate(id: number) {
  return requestJson<PolicyTuningCandidate>(`/api/policy-tuning/candidates/${id}/`);
}

export function reviewPolicyTuningCandidate(id: number, payload: { decision: PolicyTuningReviewDecision; reviewer_note?: string; metadata?: Record<string, unknown> }) {
  return requestJson<PolicyTuningCandidate>(`/api/policy-tuning/candidates/${id}/review/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function applyPolicyTuningCandidate(id: number, payload?: { note?: string; metadata?: Record<string, unknown> }) {
  return requestJson<{ candidate: PolicyTuningCandidate; application_log: PolicyTuningApplicationLog }>(`/api/policy-tuning/candidates/${id}/apply/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function getPolicyTuningApplicationLogs() {
  return requestJson<PolicyTuningApplicationLog[]>('/api/policy-tuning/application-logs/');
}

export function getPolicyTuningSummary() {
  return requestJson<PolicyTuningSummary>('/api/policy-tuning/summary/');
}

import { requestJson } from './api/client';
import type { PendingApproval, SemiAutoRun, SemiAutoSummary } from '../types/semiAuto';

export function runSemiAutoEvaluate() {
  return requestJson<SemiAutoRun>('/api/semi-auto/evaluate/', { method: 'POST', body: JSON.stringify({}) });
}

export function runSemiAutoExecution() {
  return requestJson<SemiAutoRun>('/api/semi-auto/run/', { method: 'POST', body: JSON.stringify({}) });
}

export function getSemiAutoRuns() {
  return requestJson<SemiAutoRun[]>('/api/semi-auto/runs/');
}

export function getSemiAutoRun(id: string | number) {
  return requestJson<SemiAutoRun>(`/api/semi-auto/runs/${id}/`);
}

export function getPendingApprovals() {
  return requestJson<PendingApproval[]>('/api/semi-auto/pending-approvals/');
}

export function approvePendingApproval(id: string | number, decisionNote = '') {
  return requestJson<PendingApproval>(`/api/semi-auto/pending-approvals/${id}/approve/`, {
    method: 'POST',
    body: JSON.stringify({ decision_note: decisionNote }),
  });
}

export function rejectPendingApproval(id: string | number, decisionNote = '') {
  return requestJson<PendingApproval>(`/api/semi-auto/pending-approvals/${id}/reject/`, {
    method: 'POST',
    body: JSON.stringify({ decision_note: decisionNote }),
  });
}

export function getSemiAutoSummary() {
  return requestJson<SemiAutoSummary>('/api/semi-auto/summary/');
}

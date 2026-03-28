import { requestJson } from './api/client';
import type { ApprovalDecisionPayload, ApprovalRequest, ApprovalSummary } from '../types/approvals';

export function getApprovals(status?: string) {
  const suffix = status ? `?status=${encodeURIComponent(status)}` : '';
  return requestJson<ApprovalRequest[]>(`/api/approvals/${suffix}`);
}

export function getApproval(id: number) {
  return requestJson<ApprovalRequest>(`/api/approvals/${id}/`);
}

export function approveRequest(id: number, payload: ApprovalDecisionPayload = {}) {
  return requestJson<ApprovalRequest>(`/api/approvals/${id}/approve/`, { method: 'POST', body: JSON.stringify(payload) });
}

export function rejectRequest(id: number, payload: ApprovalDecisionPayload = {}) {
  return requestJson<ApprovalRequest>(`/api/approvals/${id}/reject/`, { method: 'POST', body: JSON.stringify(payload) });
}

export function expireRequest(id: number, payload: ApprovalDecisionPayload = {}) {
  return requestJson<ApprovalRequest>(`/api/approvals/${id}/expire/`, { method: 'POST', body: JSON.stringify(payload) });
}

export function escalateRequest(id: number, payload: ApprovalDecisionPayload = {}) {
  return requestJson<ApprovalRequest>(`/api/approvals/${id}/escalate/`, { method: 'POST', body: JSON.stringify(payload) });
}

export function getApprovalSummary() {
  return requestJson<ApprovalSummary>('/api/approvals/summary/');
}

export function getPendingApprovals() {
  return requestJson<ApprovalRequest[]>('/api/approvals/pending/');
}

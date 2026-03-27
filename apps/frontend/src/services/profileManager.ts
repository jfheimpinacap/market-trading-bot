import { requestJson } from './api/client';
import type { ProfileGovernanceRun, ProfileGovernanceSummary } from '../types/profileManager';

export function runProfileGovernance(payload: { decision_mode?: string; triggered_by?: string } = {}) {
  return requestJson<ProfileGovernanceRun>('/api/profile-manager/run-governance/', { method: 'POST', body: JSON.stringify(payload) });
}

export function getProfileGovernanceRuns() {
  return requestJson<ProfileGovernanceRun[]>('/api/profile-manager/runs/');
}

export function getProfileGovernanceRun(id: number) {
  return requestJson<ProfileGovernanceRun>(`/api/profile-manager/runs/${id}/`);
}

export function getCurrentProfileGovernance() {
  return requestJson<ProfileGovernanceRun>('/api/profile-manager/current/');
}

export function getProfileGovernanceSummary() {
  return requestJson<ProfileGovernanceSummary>('/api/profile-manager/summary/');
}

export function applyProfileDecision(id: number) {
  return requestJson<{ status: string; decision_id: number }>(`/api/profile-manager/apply-decision/${id}/`, { method: 'POST', body: '{}' });
}

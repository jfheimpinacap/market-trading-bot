import { requestJson } from './api/client';
import type { PolicyRolloutRun, PolicyRolloutSummary } from '../types/policyRollout';

export function startPolicyRollout(payload: { policy_tuning_candidate_id: number; application_log_id?: number; observation_window_days?: number; metadata?: Record<string, unknown> }) {
  return requestJson<PolicyRolloutRun>('/api/policy-rollout/start/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getPolicyRolloutRuns() {
  return requestJson<PolicyRolloutRun[]>('/api/policy-rollout/runs/');
}

export function getPolicyRolloutRun(id: number) {
  return requestJson<PolicyRolloutRun>(`/api/policy-rollout/runs/${id}/`);
}

export function evaluatePolicyRollout(id: number, payload?: { metadata?: Record<string, unknown> }) {
  return requestJson<{ run: PolicyRolloutRun; recommendation: string; post_change_snapshot_id: number }>(`/api/policy-rollout/runs/${id}/evaluate/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function rollbackPolicyRollout(id: number, payload?: { reason?: string; require_approval?: boolean }) {
  return requestJson<{ run: PolicyRolloutRun; rollback_outcome: Record<string, unknown> }>(`/api/policy-rollout/runs/${id}/rollback/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function getPolicyRolloutSummary() {
  return requestJson<PolicyRolloutSummary>('/api/policy-rollout/summary/');
}

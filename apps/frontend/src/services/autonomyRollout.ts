import { requestJson } from './api/client';
import type { AutonomyRolloutRun, AutonomyRolloutSummary } from '../types/autonomyRollout';

export function startAutonomyRollout(payload: { autonomy_stage_transition_id: number; observation_window_days?: number; metadata?: Record<string, unknown> }) {
  return requestJson<AutonomyRolloutRun>('/api/autonomy-rollout/start/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getAutonomyRolloutRuns() {
  return requestJson<AutonomyRolloutRun[]>('/api/autonomy-rollout/runs/');
}

export function getAutonomyRolloutRun(id: number) {
  return requestJson<AutonomyRolloutRun>(`/api/autonomy-rollout/runs/${id}/`);
}

export function evaluateAutonomyRollout(id: number, payload?: { metadata?: Record<string, unknown> }) {
  return requestJson<{ run: AutonomyRolloutRun; recommendation: string; post_change_snapshot_id: number }>(`/api/autonomy-rollout/runs/${id}/evaluate/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function rollbackAutonomyRollout(id: number, payload?: { reason?: string; require_approval?: boolean }) {
  return requestJson<{ run: AutonomyRolloutRun; rollback_outcome: Record<string, unknown> }>(`/api/autonomy-rollout/runs/${id}/rollback/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function getAutonomyRolloutSummary() {
  return requestJson<AutonomyRolloutSummary>('/api/autonomy-rollout/summary/');
}

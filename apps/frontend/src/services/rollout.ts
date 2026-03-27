import { requestJson } from './api/client';
import type { RolloutSummary, StackRolloutPlan, StackRolloutRun } from '../types/rollout';

export function createStackRolloutPlan(payload: Record<string, unknown>) {
  return requestJson<StackRolloutPlan>('/api/rollout/create-plan/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function startRollout(id: number, payload: Record<string, unknown> = {}) {
  return requestJson<StackRolloutRun>(`/api/rollout/start/${id}/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function pauseRollout(id: number) {
  return requestJson<StackRolloutRun>(`/api/rollout/pause/${id}/`, {
    method: 'POST',
    body: '{}',
  });
}

export function resumeRollout(id: number) {
  return requestJson<StackRolloutRun>(`/api/rollout/resume/${id}/`, {
    method: 'POST',
    body: '{}',
  });
}

export function rollbackRollout(id: number, payload: Record<string, unknown> = {}) {
  return requestJson<StackRolloutRun>(`/api/rollout/rollback/${id}/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getRolloutRuns() {
  return requestJson<StackRolloutRun[]>('/api/rollout/runs/');
}

export function getRolloutRun(id: number) {
  return requestJson<StackRolloutRun>(`/api/rollout/runs/${id}/`);
}

export function getCurrentRollout() {
  return requestJson<{ current_rollout: StackRolloutRun | null }>('/api/rollout/current/');
}

export function getRolloutSummary() {
  return requestJson<RolloutSummary>('/api/rollout/summary/');
}

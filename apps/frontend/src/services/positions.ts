import { requestJson } from './api/client';
import type { PositionLifecycleDecision, PositionLifecycleRun, PositionLifecycleSummary } from '../types/positions';

export function runPositionLifecycle(payload?: { metadata?: Record<string, unknown> }) {
  return requestJson<{ lifecycle_run: PositionLifecycleRun }>('/api/positions/run-lifecycle/', {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function getPositionLifecycleRuns() {
  return requestJson<PositionLifecycleRun[]>('/api/positions/lifecycle-runs/');
}

export function getPositionLifecycleRun(id: number) {
  return requestJson<PositionLifecycleRun>(`/api/positions/lifecycle-runs/${id}/`);
}

export function getPositionDecisions() {
  return requestJson<PositionLifecycleDecision[]>('/api/positions/decisions/');
}

export function getPositionSummary() {
  return requestJson<PositionLifecycleSummary>('/api/positions/summary/');
}

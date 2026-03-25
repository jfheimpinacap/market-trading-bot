import { requestJson } from './api/client';
import type { ReplayRun, ReplayStep, ReplaySummary, RunReplayPayload } from '../types/replay';

export function runReplay(payload: RunReplayPayload) {
  return requestJson<ReplayRun>('/api/replay/run/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getReplayRuns() {
  return requestJson<ReplayRun[]>('/api/replay/runs/');
}

export function getReplayRun(id: string | number) {
  return requestJson<ReplayRun>(`/api/replay/runs/${id}/`);
}

export function getReplaySummary() {
  return requestJson<ReplaySummary>('/api/replay/summary/');
}

export function getReplayRunSteps(id: string | number) {
  return requestJson<ReplayStep[]>(`/api/replay/runs/${id}/steps/`);
}

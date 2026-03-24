import { requestJson } from './api/client';
import type {
  ContinuousDemoControlResponse,
  ContinuousDemoCycleRun,
  ContinuousDemoSession,
  ContinuousDemoStatus,
  ContinuousDemoSummary,
} from '../types/continuousDemo';

export function startContinuousDemo(payload: Record<string, unknown> = {}) {
  return requestJson<ContinuousDemoSession | ContinuousDemoControlResponse>('/api/continuous-demo/start/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function stopContinuousDemo(killSwitch = false) {
  return requestJson<ContinuousDemoControlResponse>('/api/continuous-demo/stop/', {
    method: 'POST',
    body: JSON.stringify({ kill_switch: killSwitch }),
  });
}

export function pauseContinuousDemo() {
  return requestJson<ContinuousDemoSession | ContinuousDemoControlResponse>('/api/continuous-demo/pause/', { method: 'POST', body: JSON.stringify({}) });
}

export function resumeContinuousDemo() {
  return requestJson<ContinuousDemoSession | ContinuousDemoControlResponse>('/api/continuous-demo/resume/', { method: 'POST', body: JSON.stringify({}) });
}

export function runSingleDemoCycle() {
  return requestJson<ContinuousDemoCycleRun | ContinuousDemoControlResponse>('/api/continuous-demo/run-cycle/', { method: 'POST', body: JSON.stringify({}) });
}

export function getContinuousDemoStatus() {
  return requestJson<ContinuousDemoStatus>('/api/continuous-demo/status/');
}

export function getContinuousDemoSessions() {
  return requestJson<ContinuousDemoSession[]>('/api/continuous-demo/sessions/');
}

export function getContinuousDemoSession(id: string | number) {
  return requestJson<ContinuousDemoSession>(`/api/continuous-demo/sessions/${id}/`);
}

export function getContinuousDemoCycles(sessionId?: string | number) {
  const search = sessionId === undefined ? '' : `?session_id=${sessionId}`;
  return requestJson<ContinuousDemoCycleRun[]>(`/api/continuous-demo/cycles/${search}`);
}

export function getContinuousDemoCycle(id: string | number) {
  return requestJson<ContinuousDemoCycleRun>(`/api/continuous-demo/cycles/${id}/`);
}

export function getContinuousDemoSummary() {
  return requestJson<ContinuousDemoSummary>('/api/continuous-demo/summary/');
}

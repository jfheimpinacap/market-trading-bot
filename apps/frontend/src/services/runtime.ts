import { requestJson } from './api/client';
import type {
  RuntimeCapabilities,
  OperatingModeDecision,
  OperatingModeRecommendation,
  OperatingModeSummary,
  OperatingModeSwitchRecord,
  RuntimePostureRun,
  RuntimePostureSnapshot,
  RuntimeModeOption,
  RuntimeStatusResponse,
  RuntimeTransition,
  SetRuntimeModePayload,
} from '../types/runtime';

export function getRuntimeStatus() {
  return requestJson<RuntimeStatusResponse>('/api/runtime/status/');
}

export function getRuntimeModes() {
  return requestJson<RuntimeModeOption[]>('/api/runtime/modes/');
}

export function setRuntimeMode(payload: SetRuntimeModePayload) {
  return requestJson<{ changed: boolean; blocked_reasons?: string[]; message?: string }>('/api/runtime/set-mode/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getRuntimeTransitions() {
  return requestJson<RuntimeTransition[]>('/api/runtime/transitions/');
}

export function getRuntimeCapabilities() {
  return requestJson<RuntimeCapabilities>('/api/runtime/capabilities/');
}

export function runOperatingModeReview(payload: { triggered_by?: string; auto_apply?: boolean } = {}) {
  return requestJson<{ run_id: number }>('/api/runtime-governor/run-operating-mode-review/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getRuntimePostureRuns() {
  return requestJson<RuntimePostureRun[]>('/api/runtime-governor/runtime-posture-runs/');
}

export function getRuntimePostureSnapshots() {
  return requestJson<RuntimePostureSnapshot[]>('/api/runtime-governor/runtime-posture-snapshots/');
}

export function getOperatingModeDecisions() {
  return requestJson<OperatingModeDecision[]>('/api/runtime-governor/operating-mode-decisions/');
}

export function getOperatingModeSwitchRecords() {
  return requestJson<OperatingModeSwitchRecord[]>('/api/runtime-governor/operating-mode-switch-records/');
}

export function getOperatingModeRecommendations() {
  return requestJson<OperatingModeRecommendation[]>('/api/runtime-governor/operating-mode-recommendations/');
}

export function getOperatingModeSummary() {
  return requestJson<OperatingModeSummary>('/api/runtime-governor/operating-mode-summary/');
}

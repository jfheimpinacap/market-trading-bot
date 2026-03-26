import { requestJson } from './api/client';
import type { MissionControlCycle, MissionControlSession, MissionControlStatusResponse, MissionControlSummary } from '../types/missionControl';

export function getMissionControlStatus() {
  return requestJson<MissionControlStatusResponse>('/api/mission-control/status/');
}

export function startMissionControl(payload: Record<string, unknown> = {}) {
  return requestJson<MissionControlSession>('/api/mission-control/start/', { method: 'POST', body: JSON.stringify(payload) });
}

export function pauseMissionControl() {
  return requestJson<MissionControlSession>('/api/mission-control/pause/', { method: 'POST', body: '{}' });
}

export function resumeMissionControl() {
  return requestJson<MissionControlSession>('/api/mission-control/resume/', { method: 'POST', body: '{}' });
}

export function stopMissionControl() {
  return requestJson<MissionControlSession | { status: string }>('/api/mission-control/stop/', { method: 'POST', body: '{}' });
}

export function runMissionControlCycle(payload: Record<string, unknown> = {}) {
  return requestJson<MissionControlCycle>('/api/mission-control/run-cycle/', { method: 'POST', body: JSON.stringify(payload) });
}

export function getMissionControlSessions() {
  return requestJson<MissionControlSession[]>('/api/mission-control/sessions/');
}

export function getMissionControlSession(id: number) {
  return requestJson<MissionControlSession>(`/api/mission-control/sessions/${id}/`);
}

export function getMissionControlCycles() {
  return requestJson<MissionControlCycle[]>('/api/mission-control/cycles/');
}

export function getMissionControlCycle(id: number) {
  return requestJson<MissionControlCycle>(`/api/mission-control/cycles/${id}/`);
}

export function getMissionControlSummary() {
  return requestJson<MissionControlSummary>('/api/mission-control/summary/');
}

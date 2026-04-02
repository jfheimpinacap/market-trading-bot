import { requestJson } from './api/client';
import type {
  AutonomousCycleExecution,
  AutonomousCycleOutcome,
  AutonomousCyclePlan,
  AutonomousRuntimeRecommendation,
  AutonomousRuntimeRun,
  AutonomousRuntimeSummary,
  AutonomousRuntimeSession,
  AutonomousRuntimeTick,
  AutonomousCadenceDecision,
  AutonomousSessionRecommendation,
  AutonomousSessionSummary,
  MissionControlCycle,
  MissionControlSession,
  MissionControlStatusResponse,
  MissionControlSummary,
} from '../types/missionControl';

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

export function runAutonomousRuntime(payload: Record<string, unknown> = {}) {
  return requestJson<AutonomousRuntimeRun>('/api/mission-control/run-autonomous-runtime/', { method: 'POST', body: JSON.stringify(payload) });
}

export function getAutonomousRuntimeRuns() {
  return requestJson<AutonomousRuntimeRun[]>('/api/mission-control/autonomous-runtime-runs/');
}

export function getAutonomousCyclePlans() {
  return requestJson<AutonomousCyclePlan[]>('/api/mission-control/autonomous-cycle-plans/');
}

export function getAutonomousCycleExecutions() {
  return requestJson<AutonomousCycleExecution[]>('/api/mission-control/autonomous-cycle-executions/');
}

export function getAutonomousCycleOutcomes() {
  return requestJson<AutonomousCycleOutcome[]>('/api/mission-control/autonomous-cycle-outcomes/');
}

export function getAutonomousRuntimeRecommendations() {
  return requestJson<AutonomousRuntimeRecommendation[]>('/api/mission-control/autonomous-runtime-recommendations/');
}

export function getAutonomousRuntimeSummary() {
  return requestJson<AutonomousRuntimeSummary>('/api/mission-control/autonomous-runtime-summary/');
}

export function startAutonomousSession(payload: Record<string, unknown> = {}) {
  return requestJson<AutonomousRuntimeSession>('/api/mission-control/start-autonomous-session/', { method: 'POST', body: JSON.stringify(payload) });
}

export function pauseAutonomousSession(sessionId: number) {
  return requestJson<AutonomousRuntimeSession>(`/api/mission-control/pause-autonomous-session/${sessionId}/`, { method: 'POST', body: '{}' });
}

export function resumeAutonomousSession(sessionId: number) {
  return requestJson<AutonomousRuntimeSession>(`/api/mission-control/resume-autonomous-session/${sessionId}/`, { method: 'POST', body: '{}' });
}

export function stopAutonomousSession(sessionId: number) {
  return requestJson<AutonomousRuntimeSession>(`/api/mission-control/stop-autonomous-session/${sessionId}/`, { method: 'POST', body: '{}' });
}

export function runAutonomousTick(sessionId: number) {
  return requestJson<{
    tick: AutonomousRuntimeTick;
    cadence_decision: AutonomousCadenceDecision;
    recommendation: AutonomousSessionRecommendation;
  }>(`/api/mission-control/run-autonomous-tick/${sessionId}/`, { method: 'POST', body: '{}' });
}

export function getAutonomousSessions() {
  return requestJson<AutonomousRuntimeSession[]>('/api/mission-control/autonomous-sessions/');
}

export function getAutonomousTicks() {
  return requestJson<AutonomousRuntimeTick[]>('/api/mission-control/autonomous-ticks/');
}

export function getAutonomousCadenceDecisions() {
  return requestJson<AutonomousCadenceDecision[]>('/api/mission-control/autonomous-cadence-decisions/');
}

export function getAutonomousSessionRecommendations() {
  return requestJson<AutonomousSessionRecommendation[]>('/api/mission-control/autonomous-session-recommendations/');
}

export function getAutonomousSessionSummary() {
  return requestJson<AutonomousSessionSummary>('/api/mission-control/autonomous-session-summary/');
}

import { requestJson } from './api/client';
import type {
  AutonomousCycleExecution,
  AutonomousHeartbeatDecision,
  AutonomousHeartbeatRecommendation,
  AutonomousHeartbeatRun,
  AutonomousHeartbeatSummary,
  AutonomousCycleOutcome,
  AutonomousCyclePlan,
  AutonomousRunnerState,
  AutonomousRuntimeRecommendation,
  AutonomousRuntimeRun,
  AutonomousRuntimeSummary,
  AutonomousRuntimeSession,
  AutonomousRuntimeTick,
  AutonomousProfileRecommendation,
  AutonomousProfileSelectionRun,
  AutonomousProfileSwitchDecision,
  AutonomousProfileSwitchRecord,
  AutonomousScheduleProfile,
  AutonomousSessionContextReview,
  AutonomousSessionTimingSnapshot,
  AutonomousStopConditionEvaluation,
  AutonomousTimingDecision,
  AutonomousTimingRecommendation,
  AutonomousCadenceDecision,
  AutonomousSessionRecommendation,
  SessionTimingSummary,
  ProfileSelectionSummary,
  AutonomousSessionSummary,
  AutonomousTickDispatchAttempt,
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

export function startAutonomousRunner() {
  return requestJson<AutonomousRunnerState>('/api/mission-control/start-autonomous-runner/', { method: 'POST', body: '{}' });
}

export function pauseAutonomousRunner() {
  return requestJson<AutonomousRunnerState>('/api/mission-control/pause-autonomous-runner/', { method: 'POST', body: '{}' });
}

export function resumeAutonomousRunner() {
  return requestJson<AutonomousRunnerState>('/api/mission-control/resume-autonomous-runner/', { method: 'POST', body: '{}' });
}

export function stopAutonomousRunner() {
  return requestJson<AutonomousRunnerState>('/api/mission-control/stop-autonomous-runner/', { method: 'POST', body: '{}' });
}

export function runAutonomousHeartbeat() {
  return requestJson<AutonomousHeartbeatRun>('/api/mission-control/run-autonomous-heartbeat/', { method: 'POST', body: '{}' });
}

export function getAutonomousRunnerState() {
  return requestJson<AutonomousRunnerState>('/api/mission-control/autonomous-runner-state/');
}

export function getAutonomousHeartbeatRuns() {
  return requestJson<AutonomousHeartbeatRun[]>('/api/mission-control/autonomous-heartbeat-runs/');
}

export function getAutonomousHeartbeatDecisions() {
  return requestJson<AutonomousHeartbeatDecision[]>('/api/mission-control/autonomous-heartbeat-decisions/');
}

export function getAutonomousTickDispatchAttempts() {
  return requestJson<AutonomousTickDispatchAttempt[]>('/api/mission-control/autonomous-tick-dispatch-attempts/');
}

export function getAutonomousHeartbeatRecommendations() {
  return requestJson<AutonomousHeartbeatRecommendation[]>('/api/mission-control/autonomous-heartbeat-recommendations/');
}

export function getAutonomousHeartbeatSummary() {
  return requestJson<AutonomousHeartbeatSummary>('/api/mission-control/autonomous-heartbeat-summary/');
}

export function runSessionTimingReview(sessionIds?: number[]) {
  return requestJson<SessionTimingSummary>('/api/mission-control/run-session-timing-review/', {
    method: 'POST',
    body: JSON.stringify(sessionIds?.length ? { session_ids: sessionIds } : {}),
  });
}

export function getScheduleProfiles() {
  return requestJson<AutonomousScheduleProfile[]>('/api/mission-control/schedule-profiles/');
}

export function getSessionTimingSnapshots() {
  return requestJson<AutonomousSessionTimingSnapshot[]>('/api/mission-control/session-timing-snapshots/');
}

export function getStopConditionEvaluations() {
  return requestJson<AutonomousStopConditionEvaluation[]>('/api/mission-control/stop-condition-evaluations/');
}

export function getSessionTimingDecisions() {
  return requestJson<AutonomousTimingDecision[]>('/api/mission-control/session-timing-decisions/');
}

export function getSessionTimingRecommendations() {
  return requestJson<AutonomousTimingRecommendation[]>('/api/mission-control/session-timing-recommendations/');
}

export function getSessionTimingSummary() {
  return requestJson<SessionTimingSummary>('/api/mission-control/session-timing-summary/');
}

export function runProfileSelectionReview(sessionIds?: number[], applySwitches = true) {
  return requestJson<AutonomousProfileSelectionRun>('/api/mission-control/run-profile-selection-review/', {
    method: 'POST',
    body: JSON.stringify({
      ...(sessionIds?.length ? { session_ids: sessionIds } : {}),
      apply_switches: applySwitches,
    }),
  });
}

export function getSessionContextReviews() {
  return requestJson<AutonomousSessionContextReview[]>('/api/mission-control/session-context-reviews/');
}

export function getProfileSwitchDecisions() {
  return requestJson<AutonomousProfileSwitchDecision[]>('/api/mission-control/profile-switch-decisions/');
}

export function getProfileSwitchRecords() {
  return requestJson<AutonomousProfileSwitchRecord[]>('/api/mission-control/profile-switch-records/');
}

export function getProfileRecommendations() {
  return requestJson<AutonomousProfileRecommendation[]>('/api/mission-control/profile-recommendations/');
}

export function getProfileSelectionSummary() {
  return requestJson<ProfileSelectionSummary>('/api/mission-control/profile-selection-summary/');
}

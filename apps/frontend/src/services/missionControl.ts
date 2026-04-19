import { ApiError, requestJson } from './api/client';
import { API_BASE_URL } from '../lib/config';
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
  AutonomousSessionAnomaly,
  AutonomousSessionContextReview,
  AutonomousSessionHealthRecommendation,
  AutonomousSessionHealthRun,
  AutonomousSessionHealthSnapshot,
  AutonomousSessionInterventionDecision,
  AutonomousSessionRecoveryRecommendation,
  AutonomousSessionRecoveryRun,
  AutonomousSessionRecoverySnapshot,
  AutonomousRecoveryBlocker,
  AutonomousResumeDecision,
  AutonomousResumeRecord,
  AutonomousSessionTimingSnapshot,
  AutonomousStopConditionEvaluation,
  AutonomousTimingDecision,
  AutonomousTimingRecommendation,
  AutonomousCadenceDecision,
  AutonomousSessionRecommendation,
  SessionTimingSummary,
  ProfileSelectionSummary,
  SessionHealthSummary,
  SessionRecoverySummary,
  AutonomousSessionSummary,
  AutonomousTickDispatchAttempt,
  AutonomousGlobalCapacitySnapshot,
  AutonomousSessionAdmissionReview,
  AutonomousSessionAdmissionDecision,
  AutonomousSessionAdmissionRecommendation,
  GovernanceReviewItem,
  GovernanceAutoResolutionDecision,
  GovernanceAutoResolutionRecord,
  GovernanceAutoResolutionRun,
  GovernanceAutoResolutionSummary,
  GovernanceQueueAgingRun,
  GovernanceQueueAgingReview,
  GovernanceQueueAgingRecommendation,
  GovernanceQueueAgingSummary,
  GovernanceBacklogPressureRun,
  GovernanceBacklogPressureSnapshot,
  GovernanceBacklogPressureDecision,
  GovernanceBacklogPressureRecommendation,
  GovernanceBacklogPressureSummary,
  GovernanceReviewQueueRun,
  GovernanceReviewResolution,
  GovernanceReviewRecommendation,
  GovernanceReviewSummary,
  SessionAdmissionSummary,
  AutonomousSessionAdmissionRun,
  MissionControlCycle,
  MissionControlSession,
  MissionControlStatusResponse,
  MissionControlSummary,
  LivePaperBootstrapRequest,
  LivePaperBootstrapResponse,
  LivePaperBootstrapStatusResponse,
  LivePaperAttentionAlertStatusResponse,
  LivePaperAttentionAlertSyncResponse,
  LivePaperSmokeTestRequest,
  LivePaperSmokeTestResultResponse,
  LivePaperSmokeTestStatusResponse,
  LivePaperTrialRunRequest,
  LivePaperTrialHistoryResponse,
  LivePaperExtendedRunGateResponse,
  ExtendedPaperRunLaunchRequest,
  ExtendedPaperRunLaunchResponse,
  ExtendedPaperRunStatusResponse,
  LivePaperTrialTrendResponse,
  LivePaperTrialRunResultResponse,
  LivePaperTrialRunStatusResponse,
  LivePaperValidationDigestResponse,
  LivePaperAutonomyFunnelResponse,
  TestConsoleExportLogFormat,
  TestConsoleRunRequest,
  TestConsoleStatusResponse,
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

export function bootstrapLivePaperSession(payload: LivePaperBootstrapRequest = {}) {
  return requestJson<LivePaperBootstrapResponse>('/api/mission-control/bootstrap-live-paper-session/', {
    method: 'POST',
    body: JSON.stringify({
      preset: 'live_read_only_paper_conservative',
      auto_start_heartbeat: true,
      start_now: true,
      ...payload,
    }),
  });
}

export function getLivePaperBootstrapStatus(params?: { preset?: string }) {
  const query = new URLSearchParams();
  if (params?.preset) {
    query.set('preset', params.preset);
  }
  const suffix = query.size ? `?${query.toString()}` : '';
  return requestJson<LivePaperBootstrapStatusResponse>(`/api/mission-control/live-paper-bootstrap-status/${suffix}`);
}


export function getLivePaperValidation(params?: { preset?: string }) {
  const query = new URLSearchParams();
  if (params?.preset) {
    query.set('preset', params.preset);
  }
  const suffix = query.size ? `?${query.toString()}` : '';
  return requestJson<LivePaperValidationDigestResponse>(`/api/mission-control/live-paper-validation/${suffix}`);
}

export function runLivePaperSmokeTest(payload: LivePaperSmokeTestRequest = {}) {
  return requestJson<LivePaperSmokeTestResultResponse>('/api/mission-control/run-live-paper-smoke-test/', {
    method: 'POST',
    body: JSON.stringify({
      preset: 'live_read_only_paper_conservative',
      heartbeat_passes: 1,
      ...payload,
    }),
  });
}

type OptionalStatusContract = {
  exists?: boolean;
  status?: string | null;
};

function isEmptyOptionalStatusPayload(payload: unknown): boolean {
  if (!payload || typeof payload !== 'object') {
    return false;
  }
  const optionalPayload = payload as OptionalStatusContract;
  return optionalPayload.exists === false || String(optionalPayload.status ?? '').toUpperCase() === 'NO_RUN_YET';
}

async function requestOptionalStatusJson<T extends OptionalStatusContract>(path: string): Promise<T | null> {
  try {
    const payload = await requestJson<T>(path);
    if (isEmptyOptionalStatusPayload(payload)) {
      return null;
    }
    return payload;
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return null;
    }
    throw error;
  }
}

export function getLivePaperSmokeTestStatus() {
  return requestOptionalStatusJson<LivePaperSmokeTestStatusResponse>('/api/mission-control/live-paper-smoke-test-status/');
}

export function runLivePaperTrial(payload: LivePaperTrialRunRequest = {}) {
  return requestJson<LivePaperTrialRunResultResponse>('/api/mission-control/run-live-paper-trial/', {
    method: 'POST',
    body: JSON.stringify({
      preset: 'live_read_only_paper_conservative',
      heartbeat_passes: 1,
      ...payload,
    }),
  });
}

export function getLivePaperTrialStatus() {
  return requestOptionalStatusJson<LivePaperTrialRunStatusResponse>('/api/mission-control/live-paper-trial-status/');
}

export function getLivePaperTrialHistory(params?: { limit?: number; status?: 'PASS' | 'WARN' | 'FAIL' }) {
  const query = new URLSearchParams();
  if (params?.limit) {
    query.set('limit', String(params.limit));
  }
  if (params?.status) {
    query.set('status', params.status);
  }
  const suffix = query.size ? `?${query.toString()}` : '';
  return requestJson<LivePaperTrialHistoryResponse>(`/api/mission-control/live-paper-trial-history/${suffix}`);
}

export function getLivePaperTrialTrend(params?: { limit?: number; preset?: string }) {
  const query = new URLSearchParams();
  if (params?.limit) {
    query.set('limit', String(params.limit));
  }
  if (params?.preset) {
    query.set('preset', params.preset);
  }
  const suffix = query.size ? `?${query.toString()}` : '';
  return requestJson<LivePaperTrialTrendResponse>(`/api/mission-control/live-paper-trial-trend/${suffix}`);
}

export function getExtendedPaperRunGate(params?: { preset?: string }) {
  const query = new URLSearchParams();
  if (params?.preset) {
    query.set('preset', params.preset);
  }
  const suffix = query.size ? `?${query.toString()}` : '';
  return requestJson<LivePaperExtendedRunGateResponse>(`/api/mission-control/extended-paper-run-gate/${suffix}`);
}

export function startExtendedPaperRun(payload: ExtendedPaperRunLaunchRequest = {}) {
  return requestJson<ExtendedPaperRunLaunchResponse>('/api/mission-control/start-extended-paper-run/', {
    method: 'POST',
    body: JSON.stringify({
      preset: 'live_read_only_paper_conservative',
      ...payload,
    }),
  });
}

export function getExtendedPaperRunStatus(params?: { preset?: string; preset_name?: string }) {
  const query = new URLSearchParams();
  if (params?.preset) {
    query.set('preset', params.preset);
  }
  if (params?.preset_name) {
    query.set('preset_name', params.preset_name);
  }
  const suffix = query.size ? `?${query.toString()}` : '';
  return requestOptionalStatusJson<ExtendedPaperRunStatusResponse>(`/api/mission-control/extended-paper-run-status/${suffix}`);
}

export function getLivePaperAutonomyFunnel(params?: { preset?: string; window_minutes?: number }) {
  const query = new URLSearchParams();
  if (params?.preset) {
    query.set('preset', params.preset);
  }
  if (params?.window_minutes) {
    query.set('window_minutes', String(params.window_minutes));
  }
  const suffix = query.size ? `?${query.toString()}` : '';
  return requestJson<LivePaperAutonomyFunnelResponse>(`/api/mission-control/live-paper-autonomy-funnel/${suffix}`);
}

export function startTestConsoleRun(payload: TestConsoleRunRequest = {}) {
  return requestJson<TestConsoleStatusResponse>('/api/mission-control/test-console/start/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function stopTestConsoleRun() {
  return requestJson<TestConsoleStatusResponse>('/api/mission-control/test-console/stop/', {
    method: 'POST',
    body: '{}',
  });
}

export function getTestConsoleStatus() {
  return requestJson<TestConsoleStatusResponse>('/api/mission-control/test-console/status/');
}

export async function getTestConsoleExportLog(format: TestConsoleExportLogFormat = 'text') {
  const response = await fetch(`${API_BASE_URL}/api/mission-control/test-console/export-log/?format=${encodeURIComponent(format)}`);
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }
  return format === 'json' ? (await response.json()) as unknown : response.text();
}

export function getLivePaperAttentionAlertStatus() {
  return requestJson<LivePaperAttentionAlertStatusResponse>('/api/mission-control/live-paper-attention-alert-status/');
}

export function syncLivePaperAttentionAlert() {
  return requestJson<LivePaperAttentionAlertSyncResponse>('/api/mission-control/sync-live-paper-attention-alert/', {
    method: 'POST',
    body: '{}',
  });
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

export function runSessionHealthReview(sessionIds?: number[], autoApplySafe = true) {
  return requestJson<AutonomousSessionHealthRun>('/api/mission-control/run-session-health-review/', {
    method: 'POST',
    body: JSON.stringify({
      ...(sessionIds?.length ? { session_ids: sessionIds } : {}),
      auto_apply_safe: autoApplySafe,
    }),
  });
}

export function getSessionHealthRuns() {
  return requestJson<AutonomousSessionHealthRun[]>('/api/mission-control/session-health-runs/');
}

export function getSessionHealthSnapshots() {
  return requestJson<AutonomousSessionHealthSnapshot[]>('/api/mission-control/session-health-snapshots/');
}

export function getSessionAnomalies() {
  return requestJson<AutonomousSessionAnomaly[]>('/api/mission-control/session-anomalies/');
}

export function getSessionInterventionDecisions() {
  return requestJson<AutonomousSessionInterventionDecision[]>('/api/mission-control/session-intervention-decisions/');
}

export function getSessionHealthRecommendations() {
  return requestJson<AutonomousSessionHealthRecommendation[]>('/api/mission-control/session-health-recommendations/');
}

export function getSessionHealthSummary() {
  return requestJson<SessionHealthSummary>('/api/mission-control/session-health-summary/');
}

export function runSessionRecoveryReview(sessionIds?: number[]) {
  return requestJson<AutonomousSessionRecoveryRun>('/api/mission-control/run-session-recovery-review/', {
    method: 'POST',
    body: JSON.stringify({
      ...(sessionIds?.length ? { session_ids: sessionIds } : {}),
      auto_apply_safe: false,
    }),
  });
}

export function runSessionRecoveryReviewSafeAutoApply(sessionIds?: number[]) {
  return requestJson<AutonomousSessionRecoveryRun>('/api/mission-control/run-session-recovery-review/', {
    method: 'POST',
    body: JSON.stringify({
      ...(sessionIds?.length ? { session_ids: sessionIds } : {}),
      auto_apply_safe: true,
    }),
  });
}

export function getSessionRecoveryRuns() {
  return requestJson<AutonomousSessionRecoveryRun[]>('/api/mission-control/session-recovery-runs/');
}

export function getSessionRecoverySnapshots() {
  return requestJson<AutonomousSessionRecoverySnapshot[]>('/api/mission-control/session-recovery-snapshots/');
}

export function getSessionRecoveryBlockers() {
  return requestJson<AutonomousRecoveryBlocker[]>('/api/mission-control/session-recovery-blockers/');
}

export function getSessionResumeDecisions() {
  return requestJson<AutonomousResumeDecision[]>('/api/mission-control/session-resume-decisions/');
}

export function getSessionRecoveryRecommendations() {
  return requestJson<AutonomousSessionRecoveryRecommendation[]>('/api/mission-control/session-recovery-recommendations/');
}

export function getSessionResumeRecords() {
  return requestJson<AutonomousResumeRecord[]>('/api/mission-control/session-resume-records/');
}

export function applySessionResume(decisionId: number, appliedMode: 'MANUAL_RESUME' | 'AUTO_SAFE_RESUME' | 'MONITOR_ONLY_RESUME' = 'MANUAL_RESUME') {
  return requestJson<{ decision: AutonomousResumeDecision; record: AutonomousResumeRecord }>(`/api/mission-control/apply-session-resume/${decisionId}/`, {
    method: 'POST',
    body: JSON.stringify({ applied_mode: appliedMode }),
  });
}

export function getSessionRecoverySummary() {
  return requestJson<SessionRecoverySummary>('/api/mission-control/session-recovery-summary/');
}


export function runSessionAdmissionReview(sessionIds?: number[], autoApplySafe = true) {
  return requestJson<AutonomousSessionAdmissionRun>('/api/mission-control/run-session-admission-review/', {
    method: 'POST',
    body: JSON.stringify({
      ...(sessionIds?.length ? { session_ids: sessionIds } : {}),
      auto_apply_safe: autoApplySafe,
    }),
  });
}

export function getGlobalCapacitySnapshots() {
  return requestJson<AutonomousGlobalCapacitySnapshot[]>('/api/mission-control/global-capacity-snapshots/');
}

export function getSessionAdmissionReviews() {
  return requestJson<AutonomousSessionAdmissionReview[]>('/api/mission-control/session-admission-reviews/');
}

export function getSessionAdmissionDecisions() {
  return requestJson<AutonomousSessionAdmissionDecision[]>('/api/mission-control/session-admission-decisions/');
}

export function getSessionAdmissionRecommendations() {
  return requestJson<AutonomousSessionAdmissionRecommendation[]>('/api/mission-control/session-admission-recommendations/');
}

export function getSessionAdmissionSummary() {
  return requestJson<SessionAdmissionSummary>('/api/mission-control/session-admission-summary/');
}

export function runGovernanceReviewQueue() {
  return requestJson<GovernanceReviewQueueRun>('/api/mission-control/run-governance-review-queue/', { method: 'POST', body: '{}' });
}

export function getGovernanceReviewRuns() {
  return requestJson<GovernanceReviewQueueRun[]>('/api/mission-control/governance-review-runs/');
}

export function getGovernanceReviewItems() {
  return requestJson<GovernanceReviewItem[]>('/api/mission-control/governance-review-items/');
}

export function getGovernanceReviewRecommendations() {
  return requestJson<GovernanceReviewRecommendation[]>('/api/mission-control/governance-review-recommendations/');
}

export function resolveGovernanceReviewItem(
  itemId: number,
  payload: {
    resolution_type: 'APPLY_MANUAL_APPROVAL' | 'KEEP_BLOCKED' | 'DISMISS_AS_EXPECTED' | 'REQUIRE_FOLLOWUP' | 'RETRY_SAFE_APPLY';
    resolution_summary?: string;
    metadata?: Record<string, unknown>;
  },
) {
  return requestJson<GovernanceReviewResolution>(`/api/mission-control/resolve-governance-review-item/${itemId}/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getGovernanceReviewResolutions() {
  return requestJson<GovernanceReviewResolution[]>('/api/mission-control/governance-review-resolutions/');
}

export function getGovernanceReviewSummary() {
  return requestJson<GovernanceReviewSummary>('/api/mission-control/governance-review-summary/');
}

export function runGovernanceAutoResolution() {
  return requestJson<GovernanceAutoResolutionRun>('/api/mission-control/run-governance-auto-resolution/', { method: 'POST', body: '{}' });
}

export function getGovernanceAutoResolutionRuns() {
  return requestJson<GovernanceAutoResolutionRun[]>('/api/mission-control/governance-auto-resolution-runs/');
}

export function getGovernanceAutoResolutionDecisions() {
  return requestJson<GovernanceAutoResolutionDecision[]>('/api/mission-control/governance-auto-resolution-decisions/');
}

export function getGovernanceAutoResolutionRecords() {
  return requestJson<GovernanceAutoResolutionRecord[]>('/api/mission-control/governance-auto-resolution-records/');
}

export function getGovernanceAutoResolutionSummary() {
  return requestJson<GovernanceAutoResolutionSummary>('/api/mission-control/governance-auto-resolution-summary/');
}

export function runGovernanceQueueAgingReview() {
  return requestJson<GovernanceQueueAgingRun>('/api/mission-control/run-governance-queue-aging-review/', { method: 'POST', body: '{}' });
}

export function getGovernanceQueueAgingRuns() {
  return requestJson<GovernanceQueueAgingRun[]>('/api/mission-control/governance-queue-aging-runs/');
}

export function getGovernanceQueueAgingReviews() {
  return requestJson<GovernanceQueueAgingReview[]>('/api/mission-control/governance-queue-aging-reviews/');
}

export function getGovernanceQueueAgingRecommendations() {
  return requestJson<GovernanceQueueAgingRecommendation[]>('/api/mission-control/governance-queue-aging-recommendations/');
}

export function getGovernanceQueueAgingSummary() {
  return requestJson<GovernanceQueueAgingSummary>('/api/mission-control/governance-queue-aging-summary/');
}

export function runGovernanceBacklogPressureReview() {
  return requestJson<GovernanceBacklogPressureRun>('/api/mission-control/run-governance-backlog-pressure-review/', { method: 'POST', body: '{}' });
}

export function getGovernanceBacklogPressureRuns() {
  return requestJson<GovernanceBacklogPressureRun[]>('/api/mission-control/governance-backlog-pressure-runs/');
}

export function getGovernanceBacklogPressureSnapshots() {
  return requestJson<GovernanceBacklogPressureSnapshot[]>('/api/mission-control/governance-backlog-pressure-snapshots/');
}

export function getGovernanceBacklogPressureDecisions() {
  return requestJson<GovernanceBacklogPressureDecision[]>('/api/mission-control/governance-backlog-pressure-decisions/');
}

export function getGovernanceBacklogPressureRecommendations() {
  return requestJson<GovernanceBacklogPressureRecommendation[]>('/api/mission-control/governance-backlog-pressure-recommendations/');
}

export function getGovernanceBacklogPressureSummary() {
  return requestJson<GovernanceBacklogPressureSummary>('/api/mission-control/governance-backlog-pressure-summary/');
}

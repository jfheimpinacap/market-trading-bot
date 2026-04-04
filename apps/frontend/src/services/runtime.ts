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
  ModeEnforcementRun,
  ModeModuleImpact,
  ModeEnforcementDecision,
  ModeEnforcementRecommendation,
  ModeEnforcementSummary,
  RuntimeDiagnosticReview,
  RuntimeFeedbackDecision,
  RuntimeFeedbackRecommendation,
  RuntimeFeedbackRun,
  RuntimeFeedbackSummary,
  RuntimePerformanceSnapshot,
  RuntimeFeedbackApplyRun,
  RuntimeFeedbackApplyDecision,
  RuntimeFeedbackApplyRecord,
  RuntimeFeedbackApplyRecommendation,
  RuntimeFeedbackApplySummary,
  RuntimeModeStabilizationRecommendation,
  RuntimeModeStabilizationRun,
  RuntimeModeStabilizationSummary,
  RuntimeModeStabilityReview,
  RuntimeModeTransitionDecision,
  RuntimeModeTransitionApplyRecord,
  RuntimeModeTransitionSnapshot,
  RuntimeTuningProfileSummary,
  RuntimeTuningContextSnapshot,
  RuntimeTuningContextDriftSummary,
  RuntimeTuningContextDiff,
  RuntimeTuningHistoryQuery,
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


export function runModeEnforcementReview(payload: { triggered_by?: string } = {}) {
  return requestJson<{ run_id: number }>('/api/runtime-governor/run-mode-enforcement-review/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getModeEnforcementRuns() {
  return requestJson<ModeEnforcementRun[]>('/api/runtime-governor/mode-enforcement-runs/');
}

export function getModeModuleImpacts() {
  return requestJson<ModeModuleImpact[]>('/api/runtime-governor/mode-module-impacts/');
}

export function getModeEnforcementDecisions() {
  return requestJson<ModeEnforcementDecision[]>('/api/runtime-governor/mode-enforcement-decisions/');
}

export function getModeEnforcementRecommendations() {
  return requestJson<ModeEnforcementRecommendation[]>('/api/runtime-governor/mode-enforcement-recommendations/');
}

export function getModeEnforcementSummary() {
  return requestJson<ModeEnforcementSummary>('/api/runtime-governor/mode-enforcement-summary/');
}

export function runRuntimeFeedbackReview(payload: { triggered_by?: string; auto_apply?: boolean } = {}) {
  return requestJson<{ run_id: number }>('/api/runtime-governor/run-runtime-feedback-review/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getRuntimeFeedbackRuns() {
  return requestJson<RuntimeFeedbackRun[]>('/api/runtime-governor/runtime-feedback-runs/');
}

export function getRuntimePerformanceSnapshots() {
  return requestJson<RuntimePerformanceSnapshot[]>('/api/runtime-governor/runtime-performance-snapshots/');
}

export function getRuntimeDiagnosticReviews() {
  return requestJson<RuntimeDiagnosticReview[]>('/api/runtime-governor/runtime-diagnostic-reviews/');
}

export function getRuntimeFeedbackDecisions() {
  return requestJson<RuntimeFeedbackDecision[]>('/api/runtime-governor/runtime-feedback-decisions/');
}

export function getRuntimeFeedbackRecommendations() {
  return requestJson<RuntimeFeedbackRecommendation[]>('/api/runtime-governor/runtime-feedback-recommendations/');
}

export function getRuntimeFeedbackSummary() {
  return requestJson<RuntimeFeedbackSummary>('/api/runtime-governor/runtime-feedback-summary/');
}

export function runRuntimeFeedbackApplyReview(payload: { triggered_by?: string; auto_apply?: boolean } = {}) {
  return requestJson<{ run_id: number }>('/api/runtime-governor/run-runtime-feedback-apply-review/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function applyRuntimeFeedbackDecision(decisionId: number) {
  return requestJson<{ apply_decision: RuntimeFeedbackApplyDecision; apply_record: RuntimeFeedbackApplyRecord }>(
    `/api/runtime-governor/apply-runtime-feedback-decision/${decisionId}/`,
    { method: 'POST' },
  );
}

export function getRuntimeFeedbackApplyRuns() {
  return requestJson<RuntimeFeedbackApplyRun[]>('/api/runtime-governor/runtime-feedback-apply-runs/');
}

export function getRuntimeFeedbackApplyDecisions() {
  return requestJson<RuntimeFeedbackApplyDecision[]>('/api/runtime-governor/runtime-feedback-apply-decisions/');
}

export function getRuntimeFeedbackApplyRecords() {
  return requestJson<RuntimeFeedbackApplyRecord[]>('/api/runtime-governor/runtime-feedback-apply-records/');
}

export function getRuntimeFeedbackApplyRecommendations() {
  return requestJson<RuntimeFeedbackApplyRecommendation[]>('/api/runtime-governor/runtime-feedback-apply-recommendations/');
}

export function getRuntimeFeedbackApplySummary() {
  return requestJson<RuntimeFeedbackApplySummary>('/api/runtime-governor/runtime-feedback-apply-summary/');
}

export function runModeStabilizationReview(payload: { triggered_by?: string; auto_apply_safe?: boolean } = {}) {
  return requestJson<{ run_id: number }>('/api/runtime-governor/run-mode-stabilization-review/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getModeStabilizationRuns() {
  return requestJson<RuntimeModeStabilizationRun[]>('/api/runtime-governor/mode-stabilization-runs/');
}

export function getModeTransitionSnapshots() {
  return requestJson<RuntimeModeTransitionSnapshot[]>('/api/runtime-governor/mode-transition-snapshots/');
}

export function getModeStabilityReviews() {
  return requestJson<RuntimeModeStabilityReview[]>('/api/runtime-governor/mode-stability-reviews/');
}

export function getModeTransitionDecisions() {
  return requestJson<RuntimeModeTransitionDecision[]>('/api/runtime-governor/mode-transition-decisions/');
}

export function applyStabilizedModeTransition(decisionId: number) {
  return requestJson<RuntimeModeTransitionApplyRecord>(`/api/runtime-governor/apply-stabilized-mode-transition/${decisionId}/`, {
    method: 'POST',
  });
}

export function getModeTransitionApplyRecords() {
  return requestJson<RuntimeModeTransitionApplyRecord[]>('/api/runtime-governor/mode-transition-apply-records/');
}

export function getModeStabilizationRecommendations() {
  return requestJson<RuntimeModeStabilizationRecommendation[]>('/api/runtime-governor/mode-stabilization-recommendations/');
}

export function getModeStabilizationSummary() {
  return requestJson<RuntimeModeStabilizationSummary>('/api/runtime-governor/mode-stabilization-summary/');
}

export function getRuntimeTuningProfileSummary() {
  return requestJson<RuntimeTuningProfileSummary>('/api/runtime-governor/tuning-profile-summary/');
}

function buildQueryString(query: RuntimeTuningHistoryQuery = {}) {
  const params = new URLSearchParams();
  if (query.source_scope) params.set('source_scope', query.source_scope);
  if (query.drift_status) params.set('drift_status', query.drift_status);
  if (typeof query.latest_only === 'boolean') params.set('latest_only', String(query.latest_only));
  if (typeof query.limit === 'number') params.set('limit', String(query.limit));
  if (query.created_after) params.set('created_after', query.created_after);
  if (query.created_before) params.set('created_before', query.created_before);
  const encoded = params.toString();
  return encoded ? `?${encoded}` : '';
}

export function getRuntimeTuningContextSnapshots(query: RuntimeTuningHistoryQuery = {}) {
  return requestJson<RuntimeTuningContextSnapshot[]>(`/api/runtime-governor/tuning-context-snapshots/${buildQueryString(query)}`);
}

export function getRuntimeTuningContextDriftSummary() {
  return requestJson<RuntimeTuningContextDriftSummary>('/api/runtime-governor/tuning-context-drift-summary/');
}

export function getRuntimeTuningContextDiffs(query: RuntimeTuningHistoryQuery = {}) {
  return requestJson<RuntimeTuningContextDiff[]>(`/api/runtime-governor/tuning-context-diffs/${buildQueryString(query)}`);
}

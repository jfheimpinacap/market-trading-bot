import { useCallback, useEffect, useState } from 'react';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { navigate } from '../../lib/router';
import { getIncidentSummary } from '../../services/incidents';
import {
  getOperatingModeDecisions,
  getOperatingModeRecommendations,
  getOperatingModeSummary,
  getOperatingModeSwitchRecords,
  getRuntimeCapabilities,
  getRuntimeModes,
  getRuntimePostureSnapshots,
  getRuntimeStatus,
  getRuntimeTransitions,
  runOperatingModeReview,
  setRuntimeMode,
  runModeEnforcementReview,
  getModeModuleImpacts,
  getModeEnforcementDecisions,
  getModeEnforcementRecommendations,
  getModeEnforcementSummary,
  getRuntimeDiagnosticReviews,
  getRuntimeFeedbackDecisions,
  getRuntimeFeedbackRecommendations,
  getRuntimeFeedbackSummary,
  getRuntimePerformanceSnapshots,
  runRuntimeFeedbackReview,
  runRuntimeFeedbackApplyReview,
  getRuntimeFeedbackApplyRuns,
  getRuntimeFeedbackApplyDecisions,
  getRuntimeFeedbackApplyRecords,
  getRuntimeFeedbackApplyRecommendations,
  getRuntimeFeedbackApplySummary,
  applyRuntimeFeedbackDecision,
  runModeStabilizationReview,
  getModeStabilizationRuns,
  getModeTransitionSnapshots,
  getModeStabilityReviews,
  getModeTransitionDecisions,
  getModeTransitionApplyRecords,
  applyStabilizedModeTransition,
  getModeStabilizationRecommendations,
  getModeStabilizationSummary,
  getRuntimeTuningProfileSummary,
  getRuntimeTuningContextSnapshots,
  getRuntimeTuningContextDriftSummary,
  getRuntimeTuningContextDiffs,
  getRuntimeTuningContextDiffDetail,
  getRuntimeTuningRunCorrelations,
  getRuntimeTuningScopeDigest,
  getRuntimeTuningChangeAlerts,
  getRuntimeTuningChangeAlertSummary,
  getRuntimeTuningReviewBoard,
  getRuntimeTuningInvestigation,
  getRuntimeTuningScopeTimeline,
  getRuntimeTuningReviewStateDetail,
  acknowledgeRuntimeTuningScope,
  markRuntimeTuningScopeFollowup,
  clearRuntimeTuningScopeReview,
} from '../../services/runtime';
import type {
  OperatingModeDecision,
  OperatingModeRecommendation,
  OperatingModeSummary,
  OperatingModeSwitchRecord,
  RuntimeCapabilities,
  RuntimeModeOption,
  RuntimePostureSnapshot,
  RuntimeStatusResponse,
  RuntimeTransition,
  ModeModuleImpact,
  ModeEnforcementDecision,
  ModeEnforcementRecommendation,
  ModeEnforcementSummary,
  RuntimeDiagnosticReview,
  RuntimeFeedbackDecision,
  RuntimeFeedbackRecommendation,
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
  RuntimeSummaryTuningContext,
  RuntimeTuningContextSnapshot,
  RuntimeTuningContextDriftSummary,
  RuntimeTuningContextDiff,
  RuntimeTuningHistoryQuery,
  RuntimeTuningDriftStatus,
  RuntimeTuningRunCorrelation,
  RuntimeTuningScopeDigest,
  RuntimeTuningChangeAlert,
  RuntimeTuningAlertSummary,
  RuntimeTuningReviewBoardRow,
  RuntimeTuningInvestigationPacket,
  RuntimeTuningScopeTimeline,
  RuntimeTuningReviewState,
  RuntimeTuningManualReviewStatus,
} from '../../types/runtime';
import type { IncidentSummary } from '../../types/incidents';

function tone(value: string) {
  if (value === 'PAPER_AUTO' || value === 'ACTIVE') return 'ready';
  if (value === 'PAPER_SEMI_AUTO' || value === 'DEGRADED' || value === 'PAPER_ASSIST' || value === 'PAUSED') return 'pending';
  if (value === 'OBSERVE_ONLY' || value === 'STOPPED') return 'offline';
  return 'neutral';
}

function getFocusedScopeFromQuery(): RuntimeTuningContextSnapshot['source_scope'] | null {
  const value = new URLSearchParams(window.location.search).get('tuningScope');
  if (value === 'runtime_feedback' || value === 'operating_mode' || value === 'mode_stabilization' || value === 'mode_enforcement') {
    return value;
  }
  return null;
}

function shouldOpenInvestigationFromQuery(): boolean {
  return new URLSearchParams(window.location.search).get('investigate') === '1';
}

function TuningContextBlock({ context }: { context: RuntimeSummaryTuningContext | null }) {
  if (!context) return null;
  return (
    <>
      <h4>Active tuning context</h4>
      <div className="system-metadata-grid">
        <div><strong>Profile:</strong> {context.tuning_profile_name}</div>
        <div><strong>Fingerprint:</strong> {context.tuning_profile_fingerprint ?? '—'}</div>
      </div>
      {context.tuning_profile_summary ? <p><strong>Summary:</strong> {context.tuning_profile_summary}</p> : null}
      <h5>Effective values</h5>
      <ul>
        {Object.entries(context.tuning_effective_values ?? {}).map(([key, value]) => (
          <li key={key}><strong>{key}:</strong> {String(value)}</li>
        ))}
      </ul>
      <h5>Guardrails</h5>
      <ul>
        {Object.entries(context.tuning_guardrail_summary ?? {}).map(([key, value]) => (
          <li key={key}><strong>{key}:</strong> {String(value)}</li>
        ))}
      </ul>
    </>
  );
}

export function RuntimePage() {
  const [tuningScopeFilter, setTuningScopeFilter] = useState<RuntimeTuningContextSnapshot['source_scope'] | 'all'>('all');
  const [tuningDiffDriftFilter, setTuningDiffDriftFilter] = useState<RuntimeTuningDriftStatus | 'all'>('all');
  const [tuningLatestOnly, setTuningLatestOnly] = useState(false);
  const [tuningLimit, setTuningLimit] = useState(20);
  const [status, setStatus] = useState<RuntimeStatusResponse | null>(null);
  const [modes, setModes] = useState<RuntimeModeOption[]>([]);
  const [transitions, setTransitions] = useState<RuntimeTransition[]>([]);
  const [caps, setCaps] = useState<RuntimeCapabilities | null>(null);
  const [operatingSummary, setOperatingSummary] = useState<OperatingModeSummary | null>(null);
  const [postureSnapshots, setPostureSnapshots] = useState<RuntimePostureSnapshot[]>([]);
  const [modeDecisions, setModeDecisions] = useState<OperatingModeDecision[]>([]);
  const [switchRecords, setSwitchRecords] = useState<OperatingModeSwitchRecord[]>([]);
  const [recommendations, setRecommendations] = useState<OperatingModeRecommendation[]>([]);
  const [modeImpacts, setModeImpacts] = useState<ModeModuleImpact[]>([]);
  const [modeEnforcementDecisions, setModeEnforcementDecisions] = useState<ModeEnforcementDecision[]>([]);
  const [modeEnforcementRecommendations, setModeEnforcementRecommendations] = useState<ModeEnforcementRecommendation[]>([]);
  const [modeEnforcementSummary, setModeEnforcementSummary] = useState<ModeEnforcementSummary | null>(null);
  const [runtimePerformanceSnapshots, setRuntimePerformanceSnapshots] = useState<RuntimePerformanceSnapshot[]>([]);
  const [runtimeDiagnosticReviews, setRuntimeDiagnosticReviews] = useState<RuntimeDiagnosticReview[]>([]);
  const [runtimeFeedbackDecisions, setRuntimeFeedbackDecisions] = useState<RuntimeFeedbackDecision[]>([]);
  const [runtimeFeedbackRecommendations, setRuntimeFeedbackRecommendations] = useState<RuntimeFeedbackRecommendation[]>([]);
  const [runtimeFeedbackSummary, setRuntimeFeedbackSummary] = useState<RuntimeFeedbackSummary | null>(null);
  const [runtimeFeedbackApplyRuns, setRuntimeFeedbackApplyRuns] = useState<RuntimeFeedbackApplyRun[]>([]);
  const [runtimeFeedbackApplyDecisions, setRuntimeFeedbackApplyDecisions] = useState<RuntimeFeedbackApplyDecision[]>([]);
  const [runtimeFeedbackApplyRecords, setRuntimeFeedbackApplyRecords] = useState<RuntimeFeedbackApplyRecord[]>([]);
  const [runtimeFeedbackApplyRecommendations, setRuntimeFeedbackApplyRecommendations] = useState<RuntimeFeedbackApplyRecommendation[]>([]);
  const [runtimeFeedbackApplySummary, setRuntimeFeedbackApplySummary] = useState<RuntimeFeedbackApplySummary | null>(null);
  const [modeStabilizationRuns, setModeStabilizationRuns] = useState<RuntimeModeStabilizationRun[]>([]);
  const [modeTransitionSnapshots, setModeTransitionSnapshots] = useState<RuntimeModeTransitionSnapshot[]>([]);
  const [modeStabilityReviews, setModeStabilityReviews] = useState<RuntimeModeStabilityReview[]>([]);
  const [modeTransitionDecisions, setModeTransitionDecisions] = useState<RuntimeModeTransitionDecision[]>([]);
  const [modeTransitionApplyRecords, setModeTransitionApplyRecords] = useState<RuntimeModeTransitionApplyRecord[]>([]);
  const [modeStabilizationRecommendations, setModeStabilizationRecommendations] = useState<RuntimeModeStabilizationRecommendation[]>([]);
  const [modeStabilizationSummary, setModeStabilizationSummary] = useState<RuntimeModeStabilizationSummary | null>(null);
  const [tuningSummary, setTuningSummary] = useState<RuntimeTuningProfileSummary | null>(null);
  const [tuningContextSnapshots, setTuningContextSnapshots] = useState<RuntimeTuningContextSnapshot[]>([]);
  const [tuningContextDriftSummary, setTuningContextDriftSummary] = useState<RuntimeTuningContextDriftSummary | null>(null);
  const [tuningContextDiffs, setTuningContextDiffs] = useState<RuntimeTuningContextDiff[]>([]);
  const [selectedLatestDiff, setSelectedLatestDiff] = useState<RuntimeTuningContextDiff | null>(null);
  const [latestDiffLoading, setLatestDiffLoading] = useState(false);
  const [tuningRunCorrelations, setTuningRunCorrelations] = useState<RuntimeTuningRunCorrelation[]>([]);
  const [tuningScopeDigest, setTuningScopeDigest] = useState<RuntimeTuningScopeDigest[]>([]);
  const [tuningChangeAlerts, setTuningChangeAlerts] = useState<RuntimeTuningChangeAlert[]>([]);
  const [tuningAlertSummary, setTuningAlertSummary] = useState<RuntimeTuningAlertSummary | null>(null);
  const [tuningReviewBoard, setTuningReviewBoard] = useState<RuntimeTuningReviewBoardRow[]>([]);
  const [tuningReviewAttentionOnly, setTuningReviewAttentionOnly] = useState(false);
  const [tuningReviewScopeFilter, setTuningReviewScopeFilter] = useState('');
  const [focusedScope, setFocusedScope] = useState<RuntimeTuningContextSnapshot['source_scope'] | null>(getFocusedScopeFromQuery());
  const [tuningInvestigation, setTuningInvestigation] = useState<RuntimeTuningInvestigationPacket | null>(null);
  const [tuningScopeTimeline, setTuningScopeTimeline] = useState<RuntimeTuningScopeTimeline | null>(null);
  const [manualReviewState, setManualReviewState] = useState<RuntimeTuningReviewState | null>(null);
  const [manualReviewUpdating, setManualReviewUpdating] = useState<RuntimeTuningManualReviewStatus | "CLEAR" | null>(null);
  const [timelineNonStableOnly, setTimelineNonStableOnly] = useState(false);
  const [timelineExpandedHistory, setTimelineExpandedHistory] = useState(false);
  const [investigationLoading, setInvestigationLoading] = useState(false);
  const [investigationError, setInvestigationError] = useState<string | null>(null);
  const [expandedCorrelatedScope, setExpandedCorrelatedScope] = useState<RuntimeTuningContextSnapshot['source_scope'] | null>(null);

  const [incidentSummary, setIncidentSummary] = useState<IncidentSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState<string | null>(null);
  const [runningReview, setRunningReview] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const tuningQuery: RuntimeTuningHistoryQuery = {
        latest_only: tuningLatestOnly,
        limit: tuningLimit,
        ...(tuningScopeFilter !== 'all' ? { source_scope: tuningScopeFilter } : {}),
      };
      const tuningDiffQuery: RuntimeTuningHistoryQuery = {
        ...tuningQuery,
        ...(tuningDiffDriftFilter !== 'all' ? { drift_status: tuningDiffDriftFilter } : {}),
      };
      const [statusRes, modesRes, transitionsRes, capsRes, incidentSummaryRes, postureRes, decisionRes, switchRes, recommendationRes, summaryRes, impactsRes, enforcementDecisionRes, enforcementRecommendationRes, enforcementSummaryRes, feedbackSnapshotsRes, diagnosticReviewsRes, feedbackDecisionRes, feedbackRecommendationRes, feedbackSummaryRes, feedbackApplyRunsRes, feedbackApplyDecisionsRes, feedbackApplyRecordsRes, feedbackApplyRecommendationsRes, feedbackApplySummaryRes, stabilizationRunsRes, transitionSnapshotsRes, stabilityReviewsRes, transitionDecisionsRes, transitionApplyRecordsRes, stabilizationRecommendationsRes, stabilizationSummaryRes, tuningSummaryRes, tuningContextSnapshotsRes, tuningContextDriftSummaryRes, tuningContextDiffsRes, tuningRunCorrelationsRes, tuningScopeDigestRes, tuningChangeAlertsRes, tuningChangeAlertSummaryRes, tuningReviewBoardRes] = await Promise.all([
        getRuntimeStatus(),
        getRuntimeModes(),
        getRuntimeTransitions(),
        getRuntimeCapabilities(),
        getIncidentSummary(),
        getRuntimePostureSnapshots(),
        getOperatingModeDecisions(),
        getOperatingModeSwitchRecords(),
        getOperatingModeRecommendations(),
        getOperatingModeSummary(),
        getModeModuleImpacts(),
        getModeEnforcementDecisions(),
        getModeEnforcementRecommendations(),
        getModeEnforcementSummary(),
        getRuntimePerformanceSnapshots(),
        getRuntimeDiagnosticReviews(),
        getRuntimeFeedbackDecisions(),
        getRuntimeFeedbackRecommendations(),
        getRuntimeFeedbackSummary(),
        getRuntimeFeedbackApplyRuns(),
        getRuntimeFeedbackApplyDecisions(),
        getRuntimeFeedbackApplyRecords(),
        getRuntimeFeedbackApplyRecommendations(),
        getRuntimeFeedbackApplySummary(),
        getModeStabilizationRuns(),
        getModeTransitionSnapshots(),
        getModeStabilityReviews(),
        getModeTransitionDecisions(),
        getModeTransitionApplyRecords(),
        getModeStabilizationRecommendations(),
        getModeStabilizationSummary(),
        getRuntimeTuningProfileSummary(),
        getRuntimeTuningContextSnapshots(tuningQuery),
        getRuntimeTuningContextDriftSummary(),
        getRuntimeTuningContextDiffs(tuningDiffQuery),
        getRuntimeTuningRunCorrelations(tuningQuery),
        getRuntimeTuningScopeDigest(tuningQuery),
        getRuntimeTuningChangeAlerts(tuningQuery),
        getRuntimeTuningChangeAlertSummary(tuningQuery),
        getRuntimeTuningReviewBoard({
          ...(tuningScopeFilter !== 'all' ? { source_scope: tuningScopeFilter } : {}),
          attention_only: tuningReviewAttentionOnly,
          limit: tuningLimit,
        }),
      ]);
      setStatus(statusRes);
      setModes(modesRes);
      setTransitions(transitionsRes);
      setCaps(capsRes);
      setIncidentSummary(incidentSummaryRes);
      setPostureSnapshots(postureRes);
      setModeDecisions(decisionRes);
      setSwitchRecords(switchRes);
      setRecommendations(recommendationRes);
      setOperatingSummary(summaryRes);
      setModeImpacts(impactsRes);
      setModeEnforcementDecisions(enforcementDecisionRes);
      setModeEnforcementRecommendations(enforcementRecommendationRes);
      setModeEnforcementSummary(enforcementSummaryRes);
      setRuntimePerformanceSnapshots(feedbackSnapshotsRes);
      setRuntimeDiagnosticReviews(diagnosticReviewsRes);
      setRuntimeFeedbackDecisions(feedbackDecisionRes);
      setRuntimeFeedbackRecommendations(feedbackRecommendationRes);
      setRuntimeFeedbackSummary(feedbackSummaryRes);
      setRuntimeFeedbackApplyRuns(feedbackApplyRunsRes);
      setRuntimeFeedbackApplyDecisions(feedbackApplyDecisionsRes);
      setRuntimeFeedbackApplyRecords(feedbackApplyRecordsRes);
      setRuntimeFeedbackApplyRecommendations(feedbackApplyRecommendationsRes);
      setRuntimeFeedbackApplySummary(feedbackApplySummaryRes);
      setModeStabilizationRuns(stabilizationRunsRes);
      setModeTransitionSnapshots(transitionSnapshotsRes);
      setModeStabilityReviews(stabilityReviewsRes);
      setModeTransitionDecisions(transitionDecisionsRes);
      setModeTransitionApplyRecords(transitionApplyRecordsRes);
      setModeStabilizationRecommendations(stabilizationRecommendationsRes);
      setModeStabilizationSummary(stabilizationSummaryRes);
      setTuningSummary(tuningSummaryRes);
      setTuningContextSnapshots(tuningContextSnapshotsRes);
      setTuningContextDriftSummary(tuningContextDriftSummaryRes);
      setTuningContextDiffs(tuningContextDiffsRes);
      setSelectedLatestDiff(null);
      setTuningRunCorrelations(tuningRunCorrelationsRes);
      setTuningScopeDigest(tuningScopeDigestRes);
      setTuningChangeAlerts(tuningChangeAlertsRes);
      setTuningAlertSummary(tuningChangeAlertSummaryRes);
      setTuningReviewBoard(tuningReviewBoardRes);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load runtime governance.');
    } finally {
      setLoading(false);
    }
  }, [tuningDiffDriftFilter, tuningLatestOnly, tuningLimit, tuningScopeFilter, tuningReviewAttentionOnly]);

  async function onViewLatestDiff(snapshotId: number | null) {
    if (!snapshotId) {
      setSelectedLatestDiff(null);
      return;
    }
    setLatestDiffLoading(true);
    setError(null);
    try {
      const diff = await getRuntimeTuningContextDiffDetail(snapshotId);
      setSelectedLatestDiff(diff);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load latest diff detail.');
    } finally {
      setLatestDiffLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    setFocusedScope(getFocusedScopeFromQuery());
  }, []);

  useEffect(() => {
    const scope = getFocusedScopeFromQuery();
    if (!scope || !shouldOpenInvestigationFromQuery()) return;
    void onInvestigateScope(scope, false);
  }, []);

  useEffect(() => {
    if (!focusedScope) return;
    const focusedRow = tuningReviewBoard.find((row) => row.source_scope === focusedScope);
    if (focusedRow?.latest_diff_snapshot_id) {
      void onViewLatestDiff(focusedRow.latest_diff_snapshot_id);
    }
  }, [focusedScope, tuningReviewBoard]);

  const filteredReviewBoard = tuningReviewScopeFilter
    ? tuningReviewBoard.filter((row) => row.source_scope.includes(tuningReviewScopeFilter.trim()))
    : tuningReviewBoard;

  function onFocusScope(scope: RuntimeTuningContextSnapshot['source_scope']) {
    setFocusedScope(scope);
    navigate(`/runtime?tuningScope=${encodeURIComponent(scope)}`);
    window.requestAnimationFrame(() => {
      document.getElementById('tuning-review-board')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  }

  async function onInvestigateScope(scope: RuntimeTuningContextSnapshot['source_scope'], updateUrl = true) {
    setFocusedScope(scope);
    setInvestigationLoading(true);
    setInvestigationError(null);
    setManualReviewState(null);
    if (updateUrl) {
      navigate(`/runtime?tuningScope=${encodeURIComponent(scope)}&investigate=1`);
    }
    try {
      const [packet, timeline, reviewState] = await Promise.all([
        getRuntimeTuningInvestigation(scope),
        getRuntimeTuningScopeTimeline(scope, {
          limit: timelineExpandedHistory ? 8 : 5,
          include_stable: !timelineNonStableOnly,
        }),
        getRuntimeTuningReviewStateDetail(scope),
      ]);
      setTuningInvestigation(packet);
      setTuningScopeTimeline(timeline);
      setManualReviewState(reviewState);
    } catch (err) {
      setTuningInvestigation(null);
      setTuningScopeTimeline(null);
      setManualReviewState(null);
      setInvestigationError(err instanceof Error ? err.message : 'Could not load tuning investigation packet.');
    } finally {
      setInvestigationLoading(false);
    }
  }

  function onHideInvestigation() {
    setTuningInvestigation(null);
    setTuningScopeTimeline(null);
    setInvestigationError(null);
    setManualReviewState(null);
    if (focusedScope) {
      navigate(`/runtime?tuningScope=${encodeURIComponent(focusedScope)}`);
    } else {
      navigate('/runtime');
    }
  }


  async function onUpdateManualReviewState(action: 'ACKNOWLEDGED_CURRENT' | 'FOLLOWUP_REQUIRED' | 'CLEAR') {
    if (!tuningInvestigation) return;
    setManualReviewUpdating(action);
    setInvestigationError(null);
    try {
      const scope = tuningInvestigation.source_scope;
      if (action === 'ACKNOWLEDGED_CURRENT') {
        await acknowledgeRuntimeTuningScope(scope);
      } else if (action === 'FOLLOWUP_REQUIRED') {
        await markRuntimeTuningScopeFollowup(scope);
      } else {
        await clearRuntimeTuningScopeReview(scope);
      }
      const [reviewState, boardRows] = await Promise.all([
        getRuntimeTuningReviewStateDetail(scope),
        getRuntimeTuningReviewBoard({
          ...(tuningScopeFilter !== 'all' ? { source_scope: tuningScopeFilter } : {}),
          attention_only: tuningReviewAttentionOnly,
          limit: tuningLimit,
        }),
      ]);
      setManualReviewState(reviewState);
      setTuningReviewBoard(boardRows);
    } catch (err) {
      setInvestigationError(err instanceof Error ? err.message : 'Could not update manual review state.');
    } finally {
      setManualReviewUpdating(null);
    }
  }

  useEffect(() => {
    if (!tuningInvestigation) return;
    void (async () => {
      try {
        const timeline = await getRuntimeTuningScopeTimeline(tuningInvestigation.source_scope, {
          limit: timelineExpandedHistory ? 8 : 5,
          include_stable: !timelineNonStableOnly,
        });
        setTuningScopeTimeline(timeline);
      } catch {
        // Keep existing timeline if refresh fails.
      }
    })();
  }, [timelineExpandedHistory, timelineNonStableOnly, tuningInvestigation]);

  async function onSetMode(mode: RuntimeModeOption['mode']) {
    setUpdating(mode);
    setError(null);
    try {
      await setRuntimeMode({ mode, set_by: 'operator', rationale: `Operator set mode to ${mode}.` });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not set runtime mode.');
    } finally {
      setUpdating(null);
    }
  }

  async function onRunOperatingModeReview() {
    setRunningReview(true);
    setError(null);
    try {
      await runOperatingModeReview({ triggered_by: 'runtime-page', auto_apply: true });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not run operating mode review.');
    } finally {
      setRunningReview(false);
    }
  }

  async function onRunModeEnforcementReview() {
    setRunningReview(true);
    setError(null);
    try {
      await runModeEnforcementReview({ triggered_by: 'runtime-page' });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not run mode enforcement review.');
    } finally {
      setRunningReview(false);
    }
  }

  async function onRunRuntimeFeedbackReview() {
    setRunningReview(true);
    setError(null);
    try {
      await runRuntimeFeedbackReview({ triggered_by: 'runtime-page', auto_apply: false });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not run runtime feedback review.');
    } finally {
      setRunningReview(false);
    }
  }

  async function onRunRuntimeFeedbackApplyReview() {
    setRunningReview(true);
    setError(null);
    try {
      await runRuntimeFeedbackApplyReview({ triggered_by: 'runtime-page', auto_apply: true });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not run runtime feedback apply review.');
    } finally {
      setRunningReview(false);
    }
  }

  async function onApplyRuntimeFeedbackDecision(decisionId: number) {
    setRunningReview(true);
    setError(null);
    try {
      await applyRuntimeFeedbackDecision(decisionId);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not apply runtime feedback decision.');
    } finally {
      setRunningReview(false);
    }
  }

  async function onRunModeStabilizationReview() {
    setRunningReview(true);
    setError(null);
    try {
      await runModeStabilizationReview({ triggered_by: 'runtime-page', auto_apply_safe: true });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not run mode stabilization review.');
    } finally {
      setRunningReview(false);
    }
  }

  async function onApplyStabilizedTransition(decisionId: number) {
    setRunningReview(true);
    setError(null);
    try {
      await applyStabilizedModeTransition(decisionId);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not apply stabilized transition decision.');
    } finally {
      setRunningReview(false);
    }
  }

  const latestEnforcementRunId = modeEnforcementSummary?.latest_run_id ?? null;
  const scopedImpacts = latestEnforcementRunId ? modeImpacts.filter((row) => row.linked_enforcement_run === latestEnforcementRunId) : modeImpacts;
  const scopedDecisions = latestEnforcementRunId ? modeEnforcementDecisions.filter((row) => row.linked_enforcement_run === latestEnforcementRunId) : modeEnforcementDecisions;
  const scopedRecommendations = latestEnforcementRunId
    ? modeEnforcementRecommendations.filter((row) => row.target_enforcement_run === latestEnforcementRunId)
    : modeEnforcementRecommendations;

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Runtime promotion controller"
        title="Runtime Governance"
        description="Explicit paper/demo runtime modes with auditable readiness and safety influence. No real-money enablement."
        actions={<div className="button-row"><button type="button" className="secondary-button" onClick={() => navigate('/readiness')}>Open Readiness</button><button type="button" className="secondary-button" onClick={() => navigate('/safety')}>Open Safety</button><button type="button" className="secondary-button" onClick={() => navigate('/alerts')}>Open Alerts</button><button type="button" className="secondary-button" onClick={() => navigate('/incidents')}>Open Incidents</button><button type="button" className="secondary-button" onClick={() => navigate('/mission-control')}>Open Mission Control</button><button type="button" className="secondary-button" onClick={() => navigate('/certification')}>Open Certification</button></div>}
      />

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Current mode" title="Runtime mode summary" description="Effective mode, status, and governance influence.">
          <div className="system-metadata-grid">
            <div><strong>Current mode:</strong> <StatusBadge tone={tone(status?.state.current_mode ?? 'UNKNOWN')}>{status?.state.current_mode ?? 'UNKNOWN'}</StatusBadge></div>
            <div><strong>Status:</strong> <StatusBadge tone={tone(status?.state.status ?? 'UNKNOWN')}>{status?.state.status ?? 'UNKNOWN'}</StatusBadge></div>
            <div><strong>Set by:</strong> {status?.state.set_by ?? '—'}</div>
            <div><strong>Rationale:</strong> {status?.state.rationale ?? '—'}</div>
            <div><strong>Readiness:</strong> {status?.readiness_status ?? 'No runs yet'}</div>
            <div><strong>Safety:</strong> {status?.safety_status.status ?? 'Unknown'} · {status?.safety_status.status_message ?? '—'}</div>
            <div><strong>Global mode:</strong> <StatusBadge tone={tone(status?.global_operating_mode ?? 'UNKNOWN')}>{status?.global_operating_mode ?? 'UNKNOWN'}</StatusBadge></div>
            <div><strong>Global influence:</strong> {Object.entries(status?.global_mode_influence ?? {}).map(([k, v]) => `${k}:${v}`).join(' · ') || '—'}</div>
            <div><strong>Active incidents:</strong> {incidentSummary?.active_incidents ?? 0}</div>
            <div><strong>Critical incidents:</strong> {incidentSummary?.critical_active ?? 0}</div>
          </div>
        </SectionCard>

        <SectionCard
          eyebrow="Tuning observability"
          title="Tuning Context History"
          description="Lightweight per-run snapshots for drift audit only. This does not change runtime decisions."
        >
          <div className="button-row">
            <label>
              Scope:{' '}
              <select value={tuningScopeFilter} onChange={(event) => setTuningScopeFilter(event.target.value as RuntimeTuningContextSnapshot['source_scope'] | 'all')}>
                <option value="all">All scopes</option>
                <option value="runtime_feedback">runtime_feedback</option>
                <option value="operating_mode">operating_mode</option>
                <option value="mode_stabilization">mode_stabilization</option>
                <option value="mode_enforcement">mode_enforcement</option>
              </select>
            </label>
            <label>
              Diff drift:{' '}
              <select value={tuningDiffDriftFilter} onChange={(event) => setTuningDiffDriftFilter(event.target.value as RuntimeTuningDriftStatus | 'all')}>
                <option value="all">All drift statuses</option>
                <option value="INITIAL">INITIAL</option>
                <option value="NO_CHANGE">NO_CHANGE</option>
                <option value="MINOR_CONTEXT_CHANGE">MINOR_CONTEXT_CHANGE</option>
                <option value="PROFILE_CHANGE">PROFILE_CHANGE</option>
              </select>
            </label>
            <label>
              Limit:{' '}
              <select value={tuningLimit} onChange={(event) => setTuningLimit(Number(event.target.value))}>
                <option value={10}>10</option>
                <option value={20}>20</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
              </select>
            </label>
            <label>
              <input type="checkbox" checked={tuningLatestOnly} onChange={(event) => setTuningLatestOnly(event.target.checked)} />
              {' '}Latest only
            </label>
          </div>
          <div className="system-metadata-grid">
            <div><strong>Total snapshots:</strong> {tuningContextDriftSummary?.total_snapshots ?? 0}</div>
            <div><strong>INITIAL:</strong> {tuningContextDriftSummary?.status_counts.INITIAL ?? 0}</div>
            <div><strong>NO_CHANGE:</strong> {tuningContextDriftSummary?.status_counts.NO_CHANGE ?? 0}</div>
            <div><strong>MINOR_CONTEXT_CHANGE:</strong> {tuningContextDriftSummary?.status_counts.MINOR_CONTEXT_CHANGE ?? 0}</div>
            <div><strong>PROFILE_CHANGE:</strong> {tuningContextDriftSummary?.status_counts.PROFILE_CHANGE ?? 0}</div>
          </div>
          <h4 id="tuning-review-board">Tuning Review Board</h4>
          <div className="button-row">
            <label>
              <input type="checkbox" checked={tuningReviewAttentionOnly} onChange={(event) => setTuningReviewAttentionOnly(event.target.checked)} />
              {' '}Attention only
            </label>
            <label>
              Scope contains:{' '}
              <input value={tuningReviewScopeFilter} onChange={(event) => setTuningReviewScopeFilter(event.target.value)} placeholder="mode_enforcement" />
            </label>
          </div>
          <div className="table-wrapper">
            <table className="data-table">
              <thead><tr><th>Scope</th><th>Review</th><th>Priority</th><th>Drift</th><th>Latest diff summary</th><th>Board summary</th><th>Recommended action</th><th>Quick actions</th></tr></thead>
              <tbody>
                {filteredReviewBoard.map((row) => (
                  <tr key={row.source_scope} style={focusedScope === row.source_scope ? { background: 'rgba(255, 214, 102, 0.2)' } : undefined}>
                    <td>{row.source_scope}</td>
                    <td>{row.review_status}</td>
                    <td>{row.attention_priority} #{row.attention_rank}</td>
                    <td>{row.drift_status}</td>
                    <td>{row.latest_diff_summary ?? 'No comparable diff'}</td>
                    <td>{row.board_summary}</td>
                    <td>{row.recommended_next_action}</td>
                    <td>
                      <div className="button-row">
                        <button type="button" className="button-secondary" onClick={() => onFocusScope(row.source_scope)}>Focus scope</button>
                        <button type="button" className="button-secondary" onClick={() => void onInvestigateScope(row.source_scope)}>Investigate</button>
                        <button type="button" className="button-secondary" onClick={() => void onViewLatestDiff(row.latest_diff_snapshot_id)}>{row.latest_diff_snapshot_id ? 'View latest diff' : 'No comparable diff'}</button>
                        <button type="button" className="button-secondary" onClick={() => setExpandedCorrelatedScope(expandedCorrelatedScope === row.source_scope ? null : row.source_scope)}>View correlated run context</button>
                      </div>
                      {expandedCorrelatedScope === row.source_scope ? (
                        <p>
                          {row.correlated_run_id ? (
                            <>Run #{row.correlated_run_id} · {row.correlated_run_timestamp ? new Date(row.correlated_run_timestamp).toLocaleString() : '—'} · {row.correlated_profile_name ?? '—'} ({row.correlated_profile_fingerprint ?? '—'})</>
                          ) : (
                            'No correlated run'
                          )}
                        </p>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {investigationLoading ? <p>Loading tuning investigation…</p> : null}
          {investigationError ? <p>{investigationError}</p> : null}
          {tuningInvestigation ? (
            <>
              <h4>Tuning Investigation</h4>
              <p><strong>{tuningInvestigation.investigation_summary}</strong></p>
              <div className="system-metadata-grid">
                <div><strong>Scope:</strong> {tuningInvestigation.source_scope}</div>
                <div><strong>Priority:</strong> {tuningInvestigation.attention_priority} #{tuningInvestigation.attention_rank}</div>
                <div><strong>Alert:</strong> {tuningInvestigation.alert_status}</div>
                <div><strong>Drift:</strong> {tuningInvestigation.drift_status}</div>
                <div><strong>Snapshot:</strong> #{tuningInvestigation.latest_snapshot_id} ({new Date(tuningInvestigation.latest_snapshot_created_at).toLocaleString()})</div>
                <div><strong>Previous snapshot:</strong> {tuningInvestigation.previous_snapshot_id ?? '—'}</div>
              </div>
              <p><strong>Board summary:</strong> {tuningInvestigation.board_summary}</p>
              <p><strong>Review reason codes:</strong> {tuningInvestigation.review_reason_codes.join(', ') || '—'}</p>
              <h5>Diff preview</h5>
              {tuningInvestigation.has_comparable_diff ? (
                <>
                  <p>{tuningInvestigation.latest_diff_summary ?? 'No diff summary available.'}</p>
                  <p>
                    <strong>Changed fields ({tuningInvestigation.changed_field_count}):</strong>{' '}
                    {tuningInvestigation.changed_fields_preview.join(', ') || '—'}
                    {tuningInvestigation.changed_fields_remaining_count > 0 ? ` (+${tuningInvestigation.changed_fields_remaining_count} more)` : ''}
                  </p>
                  <p>
                    <strong>Guardrail fields ({tuningInvestigation.changed_guardrail_count}):</strong>{' '}
                    {tuningInvestigation.changed_guardrail_fields_preview.join(', ') || '—'}
                    {tuningInvestigation.changed_guardrail_remaining_count > 0 ? ` (+${tuningInvestigation.changed_guardrail_remaining_count} more)` : ''}
                  </p>
                </>
              ) : (
                <p>No comparable diff is available for this scope yet.</p>
              )}
              <h5>Run context preview</h5>
              {tuningInvestigation.has_correlated_run ? (
                <p>
                  Run #{tuningInvestigation.correlated_run_id} · {tuningInvestigation.correlated_run_timestamp ? new Date(tuningInvestigation.correlated_run_timestamp).toLocaleString() : '—'} · {tuningInvestigation.correlated_profile_name ?? '—'} ({tuningInvestigation.correlated_profile_fingerprint ?? '—'})
                  {tuningInvestigation.correlated_run_summary ? ` · ${tuningInvestigation.correlated_run_summary}` : ''}
                </p>
              ) : (
                <p>No correlated run is available for this scope.</p>
              )}
              <h5>Manual Review State</h5>
              {manualReviewState ? (
                <>
                  <div className="system-metadata-grid">
                    <div><strong>Effective status:</strong> {manualReviewState.effective_review_status}</div>
                    <div><strong>Stored status:</strong> {manualReviewState.stored_review_status}</div>
                    <div><strong>Last action:</strong> {manualReviewState.last_action_type || '—'}</div>
                    <div><strong>Last action at:</strong> {manualReviewState.last_action_at ? new Date(manualReviewState.last_action_at).toLocaleString() : '—'}</div>
                    <div><strong>Newer snapshot than reviewed:</strong> {manualReviewState.has_newer_snapshot_than_reviewed ? 'yes' : 'no'}</div>
                  </div>
                  <p><strong>Summary:</strong> {manualReviewState.review_summary}</p>
                  <div className="button-row">
                    <button type="button" className="button-secondary" disabled={manualReviewUpdating !== null} onClick={() => void onUpdateManualReviewState('ACKNOWLEDGED_CURRENT')}>Acknowledge current</button>
                    <button type="button" className="button-secondary" disabled={manualReviewUpdating !== null} onClick={() => void onUpdateManualReviewState('FOLLOWUP_REQUIRED')}>Mark follow-up</button>
                    <button type="button" className="button-secondary" disabled={manualReviewUpdating !== null} onClick={() => void onUpdateManualReviewState('CLEAR')}>Clear review state</button>
                  </div>
                </>
              ) : (
                <p>No manual review state available.</p>
              )}
              <h5>Recent Scope Timeline</h5>
              {tuningScopeTimeline ? (
                <>
                  <p><strong>{tuningScopeTimeline.timeline_summary}</strong></p>
                  <div className="system-metadata-grid">
                    <div><strong>Recently stable:</strong> {tuningScopeTimeline.is_recently_stable ? 'yes' : 'no'}</div>
                    <div><strong>Recent profile shift:</strong> {tuningScopeTimeline.has_recent_profile_shift ? 'yes' : 'no'}</div>
                    <div><strong>Recent review now:</strong> {tuningScopeTimeline.has_recent_review_now ? 'yes' : 'no'}</div>
                    <div><strong>Entries shown:</strong> {tuningScopeTimeline.entry_count}</div>
                  </div>
                  <div className="button-row">
                    <label>
                      <input type="checkbox" checked={timelineNonStableOnly} onChange={(event) => setTimelineNonStableOnly(event.target.checked)} />
                      {' '}Show only non-stable
                    </label>
                    <label>
                      <input type="checkbox" checked={timelineExpandedHistory} onChange={(event) => setTimelineExpandedHistory(event.target.checked)} />
                      {' '}Show more history
                    </label>
                  </div>
                  <ul>
                    {tuningScopeTimeline.entries.map((entry) => (
                      <li key={entry.snapshot_id}>
                        <strong>{new Date(entry.created_at).toLocaleString()}</strong> · {entry.drift_status} · {entry.alert_status} · {entry.timeline_label}
                        <br />
                        {entry.diff_summary}
                        <br />
                        Changed fields/guardrails: {entry.changed_field_count}/{entry.changed_guardrail_count}
                        {entry.correlated_run_id ? ` · Run #${entry.correlated_run_id}` : ''}
                      </li>
                    ))}
                  </ul>
                </>
              ) : (
                <p>No timeline history available yet for this scope.</p>
              )}
              <div className="button-row">
                <button
                  type="button"
                  className="button-secondary"
                  onClick={() => {
                    if (!tuningInvestigation.latest_diff_snapshot_id) {
                      setInvestigationError('No comparable diff available for this scope.');
                      return;
                    }
                    setInvestigationError(null);
    setManualReviewState(null);
                    void onViewLatestDiff(tuningInvestigation.latest_diff_snapshot_id);
                  }}
                >
                  View full diff
                </button>
                <button type="button" className="button-secondary" onClick={() => onHideInvestigation()}>
                  Hide investigation
                </button>
              </div>
            </>
          ) : null}
          <h4>Tuning Drift Diff</h4>
          <div className="table-wrapper">
            <table className="data-table">
              <thead><tr><th>Scope</th><th>Current snapshot</th><th>Previous snapshot</th><th>Drift</th><th>Changed fields</th><th>Summary</th></tr></thead>
              <tbody>
                {tuningContextDiffs.map((row) => (
                  <tr key={`${row.source_scope}-${row.current_snapshot_id}`}>
                    <td>{row.source_scope}</td>
                    <td>{row.current_snapshot_id}</td>
                    <td>{row.previous_snapshot_id ?? '—'}</td>
                    <td>{row.drift_status}</td>
                    <td>{Object.keys(row.changed_fields ?? {}).length === 0 ? '—' : Object.keys(row.changed_fields).join(', ')}</td>
                    <td>{row.diff_summary}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <h4>Recent snapshots</h4>
          <div className="table-wrapper">
            <table className="data-table">
              <thead><tr><th>Scope</th><th>Run</th><th>Profile</th><th>Fingerprint</th><th>Drift</th><th>Summary</th><th>Created</th></tr></thead>
              <tbody>
                {tuningContextSnapshots.map((row) => (
                  <tr key={row.id}>
                    <td>{row.source_scope}</td>
                    <td>{row.source_run_id ?? '—'}</td>
                    <td>{row.tuning_profile_name}</td>
                    <td>{row.tuning_profile_fingerprint}</td>
                    <td>{row.drift_status}</td>
                    <td>{row.drift_summary}</td>
                    <td>{new Date(row.created_at_snapshot).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <h4>Tuning Run Correlation</h4>
          <div className="table-wrapper">
            <table className="data-table">
              <thead><tr><th>Scope</th><th>Run id</th><th>Snapshot id</th><th>Profile</th><th>Fingerprint</th><th>Drift</th><th>Run created</th><th>Summary</th></tr></thead>
              <tbody>
                {tuningRunCorrelations.map((row) => (
                  <tr key={`${row.source_scope}-${row.tuning_snapshot_id}`}>
                    <td>{row.source_scope}</td>
                    <td>{row.source_run_id ?? '—'}</td>
                    <td>{row.tuning_snapshot_id}</td>
                    <td>{row.tuning_profile_name}</td>
                    <td>{row.tuning_profile_fingerprint}</td>
                    <td>{row.drift_status}</td>
                    <td>{row.run_created_at ? new Date(row.run_created_at).toLocaleString() : '—'}</td>
                    <td>{row.correlation_summary}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <h4>Tuning Scope Digest</h4>
          <div className="table-wrapper">
            <table className="data-table">
              <thead><tr><th>Scope</th><th>Latest snapshot</th><th>Latest run</th><th>Profile</th><th>Fingerprint</th><th>Drift</th><th>Latest diff</th><th>Summary</th></tr></thead>
              <tbody>
                {tuningScopeDigest.map((row) => (
                  <tr key={row.source_scope} style={focusedScope === row.source_scope ? { background: 'rgba(255, 214, 102, 0.2)' } : undefined}>
                    <td>{row.source_scope}</td>
                    <td>{row.latest_snapshot_id}</td>
                    <td>{row.latest_run_id ?? '—'}</td>
                    <td>{row.tuning_profile_name}</td>
                    <td>{row.tuning_profile_fingerprint}</td>
                    <td>{row.latest_drift_status}</td>
                    <td>
                      {row.latest_diff_snapshot_id ? (
                        <button type="button" className="button-secondary" onClick={() => void onViewLatestDiff(row.latest_diff_snapshot_id)}>
                          View latest diff
                        </button>
                      ) : (
                        'No comparable diff'
                      )}
                    </td>
                    <td>{row.digest_summary}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <h4>Tuning Change Alerts</h4>
          <div className="table-wrapper">
            <table className="data-table">
              <thead><tr><th>Scope</th><th>Drift</th><th>Alert</th><th>Latest diff</th><th>Summary</th></tr></thead>
              <tbody>
                {tuningChangeAlerts.map((row) => (
                  <tr key={`${row.source_scope}-${row.latest_snapshot_id}`} style={focusedScope === row.source_scope ? { background: 'rgba(255, 214, 102, 0.2)' } : undefined}>
                    <td>{row.source_scope}</td>
                    <td>{row.latest_drift_status}</td>
                    <td>{row.alert_status}</td>
                    <td>
                      {row.latest_diff_snapshot_id ? (
                        <button type="button" className="button-secondary" onClick={() => void onViewLatestDiff(row.latest_diff_snapshot_id)}>
                          View latest diff
                        </button>
                      ) : (
                        'No comparable diff'
                      )}
                    </td>
                    <td>{row.alert_summary}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {latestDiffLoading ? <p>Loading latest diff…</p> : null}
          {selectedLatestDiff ? (
            <>
              <h5>Latest diff quick view</h5>
              <p>
                <strong>
                  Scope {selectedLatestDiff.source_scope}, snapshot #{selectedLatestDiff.current_snapshot_id}, drift {selectedLatestDiff.drift_status}
                </strong>
              </p>
              <p>{selectedLatestDiff.diff_summary}</p>
            </>
          ) : null}
          <h4>Tuning Alert Summary</h4>
          <div className="system-metadata-grid">
            <div><strong>Total scopes:</strong> {tuningAlertSummary?.total_scope_count ?? 0}</div>
            <div><strong>STABLE:</strong> {tuningAlertSummary?.stable_count ?? 0}</div>
            <div><strong>MINOR_CHANGE:</strong> {tuningAlertSummary?.minor_change_count ?? 0}</div>
            <div><strong>PROFILE_SHIFT:</strong> {tuningAlertSummary?.profile_shift_count ?? 0}</div>
            <div><strong>REVIEW_NOW:</strong> {tuningAlertSummary?.review_now_count ?? 0}</div>
            <div><strong>Highest priority scope:</strong> {tuningAlertSummary?.highest_priority_scope ?? '—'}</div>
            <div><strong>Most recent changed scope:</strong> {tuningAlertSummary?.most_recent_changed_scope ?? '—'}</div>
          </div>
          <p><strong>What to review first:</strong> {tuningAlertSummary?.summary ?? 'No summary available.'}</p>
          <div className="table-wrapper">
            <table className="data-table">
              <thead><tr><th>Scope</th><th>Alert</th><th>Snapshot</th><th>Updated</th><th>Summary</th></tr></thead>
              <tbody>
                {(tuningAlertSummary?.ordered_scopes ?? []).slice(0, 6).map((row) => (
                  <tr key={`${row.source_scope}-${row.latest_snapshot_id}`}>
                    <td>{row.source_scope}</td>
                    <td>{row.alert_status}</td>
                    <td>{row.latest_snapshot_id}</td>
                    <td>{row.created_at ? new Date(row.created_at).toLocaleString() : '—'}</td>
                    <td>{row.alert_summary}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionCard>

        <SectionCard
          eyebrow="Tuning observability"
          title="Active Tuning Profile"
          description="Read-only snapshot of the active runtime governor tuning profile and effective backlog guardrails. This section does not edit or auto-apply tuning."
        >
          <div className="system-metadata-grid">
            <div><strong>Profile name:</strong> {tuningSummary?.profile_name ?? '—'}</div>
            <div><strong>high_backlog_manual_review_bias:</strong> {String(tuningSummary?.effective_values.high_backlog_manual_review_bias ?? false)}</div>
            <div><strong>critical_backlog_monitor_only_bias:</strong> {String(tuningSummary?.effective_values.critical_backlog_monitor_only_bias ?? false)}</div>
            <div><strong>critical_backlog_blocks_relax:</strong> {String(tuningSummary?.effective_values.critical_backlog_blocks_relax ?? false)}</div>
            <div><strong>high_backlog_relax_dwell_multiplier:</strong> {tuningSummary?.effective_values.high_backlog_relax_dwell_multiplier ?? '—'}</div>
            <div><strong>critical_backlog_relax_dwell_multiplier:</strong> {tuningSummary?.effective_values.critical_backlog_relax_dwell_multiplier ?? '—'}</div>
          </div>
          <p><strong>Summary:</strong> {tuningSummary?.summary ?? 'No tuning snapshot available.'}</p>

          <h4>Backlog thresholds</h4>
          <ul>
            {Object.entries(tuningSummary?.backlog_thresholds ?? {}).map(([key, value]) => (
              <li key={key}><strong>{key}:</strong> {value}</li>
            ))}
          </ul>

          <h4>Backlog weights</h4>
          <ul>
            {Object.entries(tuningSummary?.backlog_weights ?? {}).map(([key, value]) => (
              <li key={key}><strong>{key}:</strong> {value}</li>
            ))}
          </ul>

          <h4>Runtime feedback guardrails</h4>
          <ul>
            {Object.entries(tuningSummary?.feedback_guardrails ?? {}).map(([key, value]) => (
              <li key={key}><strong>{key}:</strong> {String(value)}</li>
            ))}
          </ul>

          <h4>Operating mode guardrails</h4>
          <ul>
            {Object.entries(tuningSummary?.operating_mode_guardrails ?? {}).map(([key, value]) => (
              <li key={key}><strong>{key}:</strong> {String(value)}</li>
            ))}
          </ul>

          <h4>Stabilization guardrails</h4>
          <ul>
            {Object.entries(tuningSummary?.stabilization_guardrails ?? {}).map(([key, value]) => (
              <li key={key}><strong>{key}:</strong> {String(value)}</li>
            ))}
          </ul>
        </SectionCard>

        <SectionCard eyebrow="Mode selector" title="Allowed runtime modes" description="Select conservative or autonomous paper modes. Blocked options show explicit reasons.">
          <div className="table-wrapper">
            <table className="data-table">
              <thead><tr><th>Mode</th><th>Description</th><th>Allowed now</th><th>Action</th></tr></thead>
              <tbody>
                {modes.map((mode) => (
                  <tr key={mode.mode}>
                    <td><StatusBadge tone={tone(mode.mode)}>{mode.mode}</StatusBadge></td>
                    <td>{mode.description}</td>
                    <td>{mode.is_allowed_now ? 'Yes' : `No · ${mode.blocked_reasons.join(' ') || 'Blocked'}`}</td>
                    <td>
                      <button type="button" className="secondary-button" disabled={!mode.is_allowed_now || updating === mode.mode} onClick={() => void onSetMode(mode.mode)}>
                        {updating === mode.mode ? 'Setting…' : 'Set mode'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionCard>

        <SectionCard eyebrow="Capabilities" title="Effective capabilities" description="What runtime can do under this mode after safety constraints.">
          <ul>
            <li>Auto execution allowed: {caps?.allow_auto_execution ? 'Yes' : 'No'}</li>
            <li>Operator required for all trades: {caps?.require_operator_for_all_trades ? 'Yes' : 'No'}</li>
            <li>Continuous loop allowed: {caps?.allow_continuous_loop ? 'Yes' : 'No'}</li>
            <li>Real-market ops (paper-only) allowed: {caps?.allow_real_market_ops ? 'Yes' : 'No'}</li>
            <li>Max auto trades per cycle/session: {caps?.max_auto_trades_per_cycle ?? 0} / {caps?.max_auto_trades_per_session ?? 0}</li>
          </ul>
          {caps?.blocked_reasons?.length ? <p>This mode is currently blocked by readiness or safety constraints: {caps.blocked_reasons.join(' ')}</p> : null}
        </SectionCard>

        <SectionCard eyebrow="Transitions" title="Recent runtime transitions" description="Audit trail for manual changes and automatic degradations.">
          {!transitions.length ? (
            <p>No transitions recorded yet.</p>
          ) : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>From</th><th>To</th><th>Source</th><th>Reason</th><th>Created</th></tr></thead>
                <tbody>
                  {transitions.slice(0, 20).map((transition) => (
                    <tr key={transition.id}>
                      <td>{transition.from_mode ?? '—'}</td>
                      <td>{transition.to_mode}</td>
                      <td>{transition.trigger_source}</td>
                      <td>{transition.reason}</td>
                      <td>{new Date(transition.created_at).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        <SectionCard
          eyebrow="Global operating mode"
          title="Regime-aware runtime posture"
          description="Paper-only local-first operating posture controller. This layer coordinates timing/admission/exposure behavior without enabling live execution."
          aside={<button type="button" className="secondary-button" disabled={runningReview} onClick={() => void onRunOperatingModeReview()}>{runningReview ? 'Running…' : 'Run operating mode review'}</button>}
        >
          <div className="system-metadata-grid">
            <div><strong>Posture reviews:</strong> {operatingSummary?.posture_reviews ?? 0}</div>
            <div><strong>Governance backlog pressure:</strong> {operatingSummary?.governance_backlog_pressure_state ?? 'NORMAL'}</div>
            <div><strong>Mode kept:</strong> {operatingSummary?.mode_kept ?? 0}</div>
            <div><strong>Caution:</strong> {operatingSummary?.caution_count ?? 0}</div>
            <div><strong>Monitor-only:</strong> {operatingSummary?.monitor_only_count ?? 0}</div>
            <div><strong>Recovery mode:</strong> {operatingSummary?.recovery_mode_count ?? 0}</div>
            <div><strong>Throttled:</strong> {operatingSummary?.throttled_count ?? 0}</div>
            <div><strong>Blocked:</strong> {operatingSummary?.blocked_count ?? 0}</div>
          </div>
          <p><strong>Active mode:</strong> {operatingSummary?.active_mode ?? 'BALANCED'}</p>

          <h4>Posture snapshots</h4>
          <div className="table-wrapper"><table className="data-table"><thead><tr><th>Exposure</th><th>Admission</th><th>Health</th><th>Loss</th><th>Signal</th><th>Runtime/Safety/Incident</th><th>Summary</th></tr></thead><tbody>{postureSnapshots.slice(0, 10).map((row) => <tr key={row.id}><td>{row.exposure_pressure_state}</td><td>{row.admission_pressure_state}</td><td>{row.session_health_state}</td><td>{row.recent_loss_state}</td><td>{row.signal_quality_state}</td><td>{row.runtime_posture} / {row.safety_posture} / {row.incident_pressure_state}</td><td>{row.snapshot_summary}</td></tr>)}</tbody></table></div>

          <h4>Mode decisions</h4>
          <div className="table-wrapper"><table className="data-table"><thead><tr><th>Current</th><th>Target</th><th>Type</th><th>Status</th><th>Summary</th></tr></thead><tbody>{modeDecisions.slice(0, 10).map((row) => <tr key={row.id}><td>{row.current_mode ?? '—'}</td><td>{row.target_mode}</td><td>{row.decision_type}</td><td>{row.decision_status}</td><td>{row.decision_summary}</td></tr>)}</tbody></table></div>

          <h4>Switch records</h4>
          <div className="table-wrapper"><table className="data-table"><thead><tr><th>Previous</th><th>Applied</th><th>Status</th><th>Summary</th></tr></thead><tbody>{switchRecords.slice(0, 10).map((row) => <tr key={row.id}><td>{row.previous_mode ?? '—'}</td><td>{row.applied_mode}</td><td>{row.switch_status}</td><td>{row.switch_summary}</td></tr>)}</tbody></table></div>

          <h4>Recommendations</h4>
          <div className="table-wrapper"><table className="data-table"><thead><tr><th>Type</th><th>Rationale</th><th>Blockers</th><th>Confidence</th></tr></thead><tbody>{recommendations.slice(0, 10).map((row) => <tr key={row.id}><td>{row.recommendation_type}</td><td>{row.rationale}</td><td>{row.blockers.join(', ') || '—'}</td><td>{row.confidence.toFixed(2)}</td></tr>)}</tbody></table></div>
          <TuningContextBlock context={operatingSummary} />
        </SectionCard>


        <SectionCard
          eyebrow="Runtime feedback"
          title="Runtime performance self-assessment"
          description="Conservative paper-only self-assessment layer: evaluates aggregated runtime behavior, derives diagnostics, and emits auditable tuning inputs for global mode governance."
          aside={<button type="button" className="secondary-button" disabled={runningReview} onClick={() => void onRunRuntimeFeedbackReview()}>{runningReview ? 'Running…' : 'Run runtime feedback review'}</button>}
        >
          <p><strong>Boundary:</strong> local-first, single-user, paper-only, no live execution, no real money, conservative and auditable recommendations.</p>
          <div className="system-metadata-grid">
            <div><strong>Current mode:</strong> {runtimeFeedbackSummary?.current_mode ?? 'BALANCED'}</div>
            <div><strong>Governance backlog pressure:</strong> {runtimeFeedbackSummary?.governance_backlog_pressure_state ?? 'NORMAL'}</div>
            <div><strong>Recent dispatches:</strong> {runtimeFeedbackSummary?.recent_dispatches ?? 0}</div>
            <div><strong>Recent losses:</strong> {runtimeFeedbackSummary?.recent_losses ?? 0}</div>
            <div><strong>No-action pressure:</strong> {runtimeFeedbackSummary?.no_action_pressure ?? 0}</div>
            <div><strong>Blocked pressure:</strong> {runtimeFeedbackSummary?.blocked_pressure ?? 0}</div>
            <div><strong>Feedback decisions:</strong> {runtimeFeedbackSummary?.feedback_decisions ?? 0}</div>
          </div>

          <h4>Performance snapshots</h4>
          <div className="table-wrapper"><table className="data-table"><thead><tr><th>Mode</th><th>Dispatch / Outcomes / Losses</th><th>No-action / Blocked / Deferred / Parked</th><th>Signal quality</th><th>Runtime pressure</th><th>Backlog pressure</th><th>Summary</th></tr></thead><tbody>{runtimePerformanceSnapshots.slice(0, 10).map((row) => <tr key={row.id}><td>{row.current_global_mode}</td><td>{row.recent_dispatch_count} / {row.recent_closed_outcome_count} / {row.recent_loss_count}</td><td>{row.recent_no_action_tick_count} / {row.recent_blocked_tick_count} / {row.recent_deferred_dispatch_count} / {row.recent_parked_session_count}</td><td>{row.signal_quality_state}</td><td>{row.runtime_pressure_state}</td><td>{String(row.metadata?.governance_backlog_pressure_state ?? 'NORMAL')}</td><td>{row.snapshot_summary}</td></tr>)}</tbody></table></div>

          <h4>Diagnostic reviews</h4>
          <div className="table-wrapper"><table className="data-table"><thead><tr><th>Type</th><th>Severity</th><th>Summary</th></tr></thead><tbody>{runtimeDiagnosticReviews.slice(0, 10).map((row) => <tr key={row.id}><td>{row.diagnostic_type}</td><td>{row.diagnostic_severity}</td><td>{row.diagnostic_summary}</td></tr>)}</tbody></table></div>

          <h4>Feedback decisions</h4>
          <div className="table-wrapper"><table className="data-table"><thead><tr><th>Type</th><th>Status</th><th>Summary</th></tr></thead><tbody>{runtimeFeedbackDecisions.slice(0, 10).map((row) => <tr key={row.id}><td>{row.decision_type}</td><td>{row.decision_status}</td><td>{row.decision_summary}</td></tr>)}</tbody></table></div>

          <h4>Recommendations</h4>
          <div className="table-wrapper"><table className="data-table"><thead><tr><th>Type</th><th>Rationale</th><th>Blockers</th><th>Confidence</th></tr></thead><tbody>{runtimeFeedbackRecommendations.slice(0, 10).map((row) => <tr key={row.id}><td>{row.recommendation_type}</td><td>{row.rationale}</td><td>{row.blockers.join(', ') || '—'}</td><td>{row.confidence.toFixed(2)}</td></tr>)}</tbody></table></div>
          <TuningContextBlock context={runtimeFeedbackSummary} />
        </SectionCard>

        <SectionCard
          eyebrow="Runtime feedback apply"
          title="Runtime Feedback Apply"
          description="Closed-loop conservative bridge from runtime feedback decisions to global mode adjustment and downstream enforcement refresh."
          aside={<button type="button" className="secondary-button" disabled={runningReview} onClick={() => void onRunRuntimeFeedbackApplyReview()}>{runningReview ? 'Running…' : 'Run runtime feedback apply review'}</button>}
        >
          <p><strong>Boundary:</strong> auditable, local-first, paper-only apply layer. No real broker routing, no real money, no opaque optimizer.</p>
          <div className="system-metadata-grid">
            <div><strong>Apply runs:</strong> {runtimeFeedbackApplySummary?.apply_runs ?? 0}</div>
            <div><strong>Apply decisions:</strong> {runtimeFeedbackApplySummary?.apply_decisions ?? 0}</div>
            <div><strong>Apply records:</strong> {runtimeFeedbackApplySummary?.apply_records ?? 0}</div>
            <div><strong>Recommendations:</strong> {runtimeFeedbackApplySummary?.recommendations ?? 0}</div>
            <div><strong>Applied:</strong> {runtimeFeedbackApplySummary?.applied_count ?? 0}</div>
            <div><strong>Manual review:</strong> {runtimeFeedbackApplySummary?.manual_review_count ?? 0}</div>
            <div><strong>Blocked:</strong> {runtimeFeedbackApplySummary?.blocked_count ?? 0}</div>
            <div><strong>Enforcement refresh:</strong> {runtimeFeedbackApplySummary?.enforcement_refresh_count ?? 0}</div>
          </div>

          <h4>Apply decisions</h4>
          <div className="table-wrapper"><table className="data-table"><thead><tr><th>Feedback decision</th><th>Current → Target</th><th>Apply type</th><th>Status</th><th>Auto</th><th>Action</th></tr></thead><tbody>{runtimeFeedbackApplyDecisions.slice(0, 10).map((row) => <tr key={row.id}><td>{row.linked_feedback_decision}</td><td>{row.current_mode ?? '—'} → {row.target_mode ?? '—'}</td><td>{row.apply_type}</td><td>{row.apply_status}</td><td>{row.auto_applicable ? 'Yes' : 'No'}</td><td><button type="button" className="secondary-button" disabled={runningReview} onClick={() => void onApplyRuntimeFeedbackDecision(row.linked_feedback_decision)}>Apply feedback decision</button></td></tr>)}</tbody></table></div>

          <h4>Apply records</h4>
          <div className="table-wrapper"><table className="data-table"><thead><tr><th>Apply decision</th><th>Status</th><th>Previous → Applied</th><th>Enforcement refreshed</th><th>Summary</th></tr></thead><tbody>{runtimeFeedbackApplyRecords.slice(0, 10).map((row) => <tr key={row.id}><td>{row.linked_apply_decision}</td><td>{row.record_status}</td><td>{row.previous_mode ?? '—'} → {row.applied_mode ?? '—'}</td><td>{row.enforcement_refreshed ? 'Yes' : 'No'}</td><td>{row.record_summary}</td></tr>)}</tbody></table></div>

          <h4>Apply recommendations</h4>
          <div className="table-wrapper"><table className="data-table"><thead><tr><th>Type</th><th>Rationale</th><th>Blockers</th><th>Confidence</th></tr></thead><tbody>{runtimeFeedbackApplyRecommendations.slice(0, 10).map((row) => <tr key={row.id}><td>{row.recommendation_type}</td><td>{row.rationale}</td><td>{row.blockers.join(', ') || '—'}</td><td>{row.confidence.toFixed(2)}</td></tr>)}</tbody></table></div>

          <h4>Apply runs</h4>
          <div className="table-wrapper"><table className="data-table"><thead><tr><th>Started</th><th>Considered</th><th>Applied</th><th>Manual/Blocked</th><th>Mode switches</th><th>Enforcement refresh</th></tr></thead><tbody>{runtimeFeedbackApplyRuns.slice(0, 10).map((row) => <tr key={row.id}><td>{new Date(row.started_at).toLocaleString()}</td><td>{row.considered_feedback_decision_count}</td><td>{row.applied_count}</td><td>{row.manual_review_count} / {row.blocked_count}</td><td>{row.mode_switch_count}</td><td>{row.enforcement_refresh_count}</td></tr>)}</tbody></table></div>
        </SectionCard>

        <SectionCard
          eyebrow="Mode stabilization"
          title="Mode Stabilization"
          description="Anti-flapping hysteresis and dwell diagnostics that review transition intents before any real apply action. Paper-only and advisory in this phase."
          aside={<button type="button" className="secondary-button" disabled={runningReview} onClick={() => void onRunModeStabilizationReview()}>{runningReview ? 'Running…' : 'Run mode stabilization review'}</button>}
        >
          <div className="system-metadata-grid">
            <div><strong>Runs:</strong> {modeStabilizationSummary?.runs ?? 0}</div>
            <div><strong>Snapshots:</strong> {modeStabilizationSummary?.snapshots ?? 0}</div>
            <div><strong>Reviews:</strong> {modeStabilizationSummary?.reviews ?? 0}</div>
            <div><strong>Decisions:</strong> {modeStabilizationSummary?.decisions ?? 0}</div>
            <div><strong>Recommendations:</strong> {modeStabilizationSummary?.recommendations ?? 0}</div>
            <div><strong>Apply records:</strong> {modeStabilizationSummary?.apply_records ?? 0}</div>
            <div><strong>Allowed:</strong> {modeStabilizationSummary?.allowed_count ?? 0}</div>
            <div><strong>Deferred:</strong> {modeStabilizationSummary?.deferred_count ?? 0}</div>
            <div><strong>Dwell hold:</strong> {modeStabilizationSummary?.dwell_hold_count ?? 0}</div>
            <div><strong>Blocked:</strong> {modeStabilizationSummary?.blocked_count ?? 0}</div>
            <div><strong>Manual review:</strong> {modeStabilizationSummary?.manual_review_count ?? 0}</div>
            <div><strong>Applied transitions:</strong> {modeStabilizationSummary?.applied_count ?? 0}</div>
            <div><strong>Blocked apply:</strong> {modeStabilizationSummary?.blocked_apply_count ?? 0}</div>
          </div>

          <h4>Transition snapshots</h4>
          <div className="table-wrapper"><table className="data-table"><thead><tr><th>Current → Target</th><th>Dwell (s)</th><th>Recent switches</th><th>Pressure/Risk</th><th>Summary</th></tr></thead><tbody>{modeTransitionSnapshots.slice(0, 10).map((row) => <tr key={row.id}><td>{row.current_mode} → {row.target_mode}</td><td>{row.time_in_current_mode_seconds}</td><td>{row.recent_switch_count} / {row.recent_switch_window_seconds}s</td><td>{row.feedback_pressure_state} / {row.transition_risk_state}</td><td>{row.snapshot_summary}</td></tr>)}</tbody></table></div>

          <h4>Stability reviews</h4>
          <div className="table-wrapper"><table className="data-table"><thead><tr><th>Review type</th><th>Severity</th><th>Summary</th></tr></thead><tbody>{modeStabilityReviews.slice(0, 10).map((row) => <tr key={row.id}><td>{row.review_type}</td><td>{row.review_severity}</td><td>{row.review_summary}</td></tr>)}</tbody></table></div>

          <h4>Transition decisions</h4>
          <div className="table-wrapper"><table className="data-table"><thead><tr><th>Decision type</th><th>Status</th><th>Auto</th><th>Summary</th><th>Action</th></tr></thead><tbody>{modeTransitionDecisions.slice(0, 10).map((row) => <tr key={row.id}><td>{row.decision_type}</td><td>{row.decision_status}</td><td>{row.auto_applicable ? 'Yes' : 'No'}</td><td>{row.decision_summary}</td><td><button type="button" className="secondary-button" disabled={runningReview} onClick={() => void onApplyStabilizedTransition(row.id)}>Apply stabilized transition</button></td></tr>)}</tbody></table></div>

          <h4>Transition apply records</h4>
          <div className="table-wrapper"><table className="data-table"><thead><tr><th>Decision</th><th>Status</th><th>Path</th><th>Previous → Applied</th><th>Enforcement refreshed</th><th>Summary</th></tr></thead><tbody>{modeTransitionApplyRecords.slice(0, 10).map((row) => <tr key={row.id}><td>{row.linked_transition_decision}</td><td>{row.apply_status}</td><td>{Boolean(row.metadata.auto_apply_safe) ? 'Auto safe apply' : 'Manual apply'}</td><td>{row.previous_mode ?? '—'} → {row.applied_mode ?? '—'}</td><td>{row.enforcement_refreshed ? 'Yes' : 'No'}</td><td>{row.apply_summary}</td></tr>)}</tbody></table></div>

          <h4>Recommendations</h4>
          <div className="table-wrapper"><table className="data-table"><thead><tr><th>Type</th><th>Rationale</th><th>Blockers</th><th>Confidence</th></tr></thead><tbody>{modeStabilizationRecommendations.slice(0, 10).map((row) => <tr key={row.id}><td>{row.recommendation_type}</td><td>{row.rationale}</td><td>{row.blockers.join(', ') || '—'}</td><td>{row.confidence.toFixed(2)}</td></tr>)}</tbody></table></div>

          <h4>Runs</h4>
          <div className="table-wrapper"><table className="data-table"><thead><tr><th>Started</th><th>Considered</th><th>Allowed</th><th>Deferred</th><th>Dwell hold</th><th>Blocked</th><th>Manual review</th></tr></thead><tbody>{modeStabilizationRuns.slice(0, 10).map((row) => <tr key={row.id}><td>{new Date(row.started_at).toLocaleString()}</td><td>{row.considered_transition_count}</td><td>{row.allowed_count}</td><td>{row.deferred_count}</td><td>{row.dwell_hold_count}</td><td>{row.blocked_count}</td><td>{row.manual_review_count}</td></tr>)}</tbody></table></div>
          <TuningContextBlock context={modeStabilizationSummary} />
        </SectionCard>

        <SectionCard
          eyebrow="Mode enforcement"
          title="Downstream mode enforcement bridge"
          description="Converts global operating mode into explicit module-level restrictions for cadence, admission, exposure, execution intake, heartbeat, and recovery. Paper-only, local-first, no live routing."
          aside={<button type="button" className="secondary-button" disabled={runningReview} onClick={() => void onRunModeEnforcementReview()}>{runningReview ? 'Running…' : 'Run mode enforcement review'}</button>}
        >
          <div className="system-metadata-grid">
            <div><strong>Current mode:</strong> {modeEnforcementSummary?.current_mode ?? 'BALANCED'}</div>
            <div><strong>Modules affected:</strong> {modeEnforcementSummary?.modules_affected ?? 0}</div>
            <div><strong>Reduced:</strong> {modeEnforcementSummary?.reduced_count ?? 0}</div>
            <div><strong>Throttled:</strong> {modeEnforcementSummary?.throttled_count ?? 0}</div>
            <div><strong>Monitor-only:</strong> {modeEnforcementSummary?.monitor_only_count ?? 0}</div>
            <div><strong>Blocked:</strong> {modeEnforcementSummary?.blocked_count ?? 0}</div>
          </div>

          <h4>Module impacts</h4>
          <div className="table-wrapper"><table className="data-table"><thead><tr><th>Module</th><th>Impact</th><th>Summary</th></tr></thead><tbody>{scopedImpacts.slice(0, 10).map((row) => <tr key={row.id}><td>{row.module_name}</td><td>{row.impact_status}</td><td>{row.effective_behavior_summary}</td></tr>)}</tbody></table></div>

          <h4>Enforcement decisions</h4>
          <div className="table-wrapper"><table className="data-table"><thead><tr><th>Module</th><th>Decision type</th><th>Status</th><th>Summary</th></tr></thead><tbody>{scopedDecisions.slice(0, 10).map((row) => <tr key={row.id}><td>{row.module_name}</td><td>{row.decision_type}</td><td>{row.decision_status}</td><td>{row.decision_summary}</td></tr>)}</tbody></table></div>

          <h4>Recommendations</h4>
          <div className="table-wrapper"><table className="data-table"><thead><tr><th>Type</th><th>Rationale</th><th>Blockers</th><th>Confidence</th></tr></thead><tbody>{scopedRecommendations.slice(0, 10).map((row) => <tr key={row.id}><td>{row.recommendation_type}</td><td>{row.rationale}</td><td>{row.blockers.join(', ') || '—'}</td><td>{row.confidence.toFixed(2)}</td></tr>)}</tbody></table></div>
          <TuningContextBlock context={modeEnforcementSummary} />
        </SectionCard>

      </DataStateWrapper>
    </div>
  );
}

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
} from '../../types/runtime';
import type { IncidentSummary } from '../../types/incidents';

function tone(value: string) {
  if (value === 'PAPER_AUTO' || value === 'ACTIVE') return 'ready';
  if (value === 'PAPER_SEMI_AUTO' || value === 'DEGRADED' || value === 'PAPER_ASSIST' || value === 'PAUSED') return 'pending';
  if (value === 'OBSERVE_ONLY' || value === 'STOPPED') return 'offline';
  return 'neutral';
}

export function RuntimePage() {
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

  const [incidentSummary, setIncidentSummary] = useState<IncidentSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState<string | null>(null);
  const [runningReview, setRunningReview] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [statusRes, modesRes, transitionsRes, capsRes, incidentSummaryRes, postureRes, decisionRes, switchRes, recommendationRes, summaryRes, impactsRes, enforcementDecisionRes, enforcementRecommendationRes, enforcementSummaryRes, feedbackSnapshotsRes, diagnosticReviewsRes, feedbackDecisionRes, feedbackRecommendationRes, feedbackSummaryRes, feedbackApplyRunsRes, feedbackApplyDecisionsRes, feedbackApplyRecordsRes, feedbackApplyRecommendationsRes, feedbackApplySummaryRes] = await Promise.all([
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
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load runtime governance.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

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
            <div><strong>Recent dispatches:</strong> {runtimeFeedbackSummary?.recent_dispatches ?? 0}</div>
            <div><strong>Recent losses:</strong> {runtimeFeedbackSummary?.recent_losses ?? 0}</div>
            <div><strong>No-action pressure:</strong> {runtimeFeedbackSummary?.no_action_pressure ?? 0}</div>
            <div><strong>Blocked pressure:</strong> {runtimeFeedbackSummary?.blocked_pressure ?? 0}</div>
            <div><strong>Feedback decisions:</strong> {runtimeFeedbackSummary?.feedback_decisions ?? 0}</div>
          </div>

          <h4>Performance snapshots</h4>
          <div className="table-wrapper"><table className="data-table"><thead><tr><th>Mode</th><th>Dispatch / Outcomes / Losses</th><th>No-action / Blocked / Deferred / Parked</th><th>Signal quality</th><th>Runtime pressure</th><th>Summary</th></tr></thead><tbody>{runtimePerformanceSnapshots.slice(0, 10).map((row) => <tr key={row.id}><td>{row.current_global_mode}</td><td>{row.recent_dispatch_count} / {row.recent_closed_outcome_count} / {row.recent_loss_count}</td><td>{row.recent_no_action_tick_count} / {row.recent_blocked_tick_count} / {row.recent_deferred_dispatch_count} / {row.recent_parked_session_count}</td><td>{row.signal_quality_state}</td><td>{row.runtime_pressure_state}</td><td>{row.snapshot_summary}</td></tr>)}</tbody></table></div>

          <h4>Diagnostic reviews</h4>
          <div className="table-wrapper"><table className="data-table"><thead><tr><th>Type</th><th>Severity</th><th>Summary</th></tr></thead><tbody>{runtimeDiagnosticReviews.slice(0, 10).map((row) => <tr key={row.id}><td>{row.diagnostic_type}</td><td>{row.diagnostic_severity}</td><td>{row.diagnostic_summary}</td></tr>)}</tbody></table></div>

          <h4>Feedback decisions</h4>
          <div className="table-wrapper"><table className="data-table"><thead><tr><th>Type</th><th>Status</th><th>Summary</th></tr></thead><tbody>{runtimeFeedbackDecisions.slice(0, 10).map((row) => <tr key={row.id}><td>{row.decision_type}</td><td>{row.decision_status}</td><td>{row.decision_summary}</td></tr>)}</tbody></table></div>

          <h4>Recommendations</h4>
          <div className="table-wrapper"><table className="data-table"><thead><tr><th>Type</th><th>Rationale</th><th>Blockers</th><th>Confidence</th></tr></thead><tbody>{runtimeFeedbackRecommendations.slice(0, 10).map((row) => <tr key={row.id}><td>{row.recommendation_type}</td><td>{row.rationale}</td><td>{row.blockers.join(', ') || '—'}</td><td>{row.confidence.toFixed(2)}</td></tr>)}</tbody></table></div>
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
        </SectionCard>

      </DataStateWrapper>
    </div>
  );
}

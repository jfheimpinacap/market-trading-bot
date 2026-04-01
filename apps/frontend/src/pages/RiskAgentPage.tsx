import { useCallback, useEffect, useMemo, useState } from 'react';
import { EmptyState } from '../components/EmptyState';
import { PageHeader } from '../components/PageHeader';
import { SectionCard } from '../components/SectionCard';
import { StatusBadge } from '../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../components/markets/DataStateWrapper';
import { navigate } from '../lib/router';
import { getRiskAssessments, getRiskSummary, getRiskWatchEvents, runRiskAssessment, runRiskSizing, runRiskWatch } from '../services/riskAgent';
import {
  getAutonomousExecutionReadiness,
  getRiskApprovalDecisions,
  getRiskRuntimeCandidates,
  getRiskRuntimeRecommendations,
  getRiskRuntimeSummary,
  getRiskSizingPlans,
  getRiskWatchPlans,
  runRiskRuntimeReview,
} from '../services/riskRuntime';

function riskTone(level: string): 'ready' | 'pending' | 'offline' | 'neutral' {
  if (level === 'LOW' || level === 'APPROVED') return 'ready';
  if (level === 'MEDIUM' || level === 'APPROVED_REDUCED' || level === 'NEEDS_REVIEW' || level === 'READY_REDUCED' || level === 'WATCH_ONLY' || level === 'DEFERRED' || level === 'REDUCED_CONTEXT') return 'pending';
  if (level === 'READY' || level === 'READY_FOR_RISK_RUNTIME') return 'ready';
  if (level === 'HIGH' || level === 'BLOCKED') return 'offline';
  return 'neutral';
}

function severityTone(level: string): 'ready' | 'pending' | 'offline' | 'neutral' {
  if (level === 'info') return 'neutral';
  if (level === 'warning') return 'pending';
  if (level === 'high') return 'offline';
  return 'neutral';
}

export function RiskAgentPage() {
  const [marketId, setMarketId] = useState('');
  const [predictionId, setPredictionId] = useState('');
  const [baseQuantity, setBaseQuantity] = useState('5.0000');
  const [assessments, setAssessments] = useState<any[]>([]);
  const [events, setEvents] = useState<any[]>([]);
  const [summary, setSummary] = useState<any | null>(null);
  const [runtimeSummary, setRuntimeSummary] = useState<any | null>(null);
  const [approvals, setApprovals] = useState<any[]>([]);
  const [intakeCandidates, setIntakeCandidates] = useState<any[]>([]);
  const [executionReadiness, setExecutionReadiness] = useState<any[]>([]);
  const [sizingPlans, setSizingPlans] = useState<any[]>([]);
  const [watchPlans, setWatchPlans] = useState<any[]>([]);
  const [runtimeRecommendations, setRuntimeRecommendations] = useState<any[]>([]);
  const [statusFilter, setStatusFilter] = useState('');
  const [lastAssessment, setLastAssessment] = useState<any | null>(null);
  const [lastSizing, setLastSizing] = useState<any | null>(null);
  const [lastWatch, setLastWatch] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryRes, assessmentsRes, eventsRes, runtimeSummaryRes] = await Promise.all([
        getRiskSummary(),
        getRiskAssessments(),
        getRiskWatchEvents(),
        getRiskRuntimeSummary(),
      ]);
      const runId = runtimeSummaryRes.latest_run?.id;
      const [candidateRes, approvalRes, sizingRes, watchRes, readinessRes, recommendationRes] = runId
        ? await Promise.all([
            getRiskRuntimeCandidates({ run_id: runId }),
            getRiskApprovalDecisions({ run_id: runId, status: statusFilter || undefined }),
            getRiskSizingPlans({ run_id: runId }),
            getRiskWatchPlans({ run_id: runId }),
            getAutonomousExecutionReadiness({ run_id: runId }),
            getRiskRuntimeRecommendations({ run_id: runId }),
          ])
        : [[], [], [], [], [], []];

      setSummary(summaryRes);
      setAssessments(assessmentsRes);
      setEvents(eventsRes);
      setRuntimeSummary(runtimeSummaryRes);
      setIntakeCandidates(candidateRes);
      setApprovals(approvalRes);
      setSizingPlans(sizingRes);
      setWatchPlans(watchRes);
      setExecutionReadiness(readinessRes);
      setRuntimeRecommendations(recommendationRes);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load risk-agent data.');
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleAssess() {
    setBusy(true);
    setError(null);
    try {
      const res = await runRiskAssessment({
        market_id: marketId ? Number(marketId) : undefined,
        prediction_score_id: predictionId ? Number(predictionId) : undefined,
        metadata: { triggered_from: 'risk_agent_page' },
      });
      setLastAssessment(res.assessment);
      setLastSizing(null);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Assessment failed.');
    } finally {
      setBusy(false);
    }
  }

  async function handleSize() {
    if (!lastAssessment) {
      setError('Run a risk assessment first.');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const res = await runRiskSizing({ risk_assessment_id: lastAssessment.id, base_quantity: baseQuantity });
      setLastSizing(res.sizing);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Sizing failed.');
    } finally {
      setBusy(false);
    }
  }

  async function handleWatch() {
    setBusy(true);
    setError(null);
    try {
      const res = await runRiskWatch();
      setLastWatch(res.watch_run);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Watch loop failed.');
    } finally {
      setBusy(false);
    }
  }

  async function handleRunRuntime() {
    setBusy(true);
    setError(null);
    try {
      await runRiskRuntimeReview({ triggered_by: 'risk_agent_page_manual' });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Runtime review failed.');
    } finally {
      setBusy(false);
    }
  }

  const decisionCountByStatus = useMemo(() => {
    const map: Record<string, number> = {};
    approvals.forEach((item) => {
      map[item.approval_status] = (map[item.approval_status] ?? 0) + 1;
    });
    return map;
  }, [approvals]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Risk agent"
        title="Risk Agent"
        description="Runtime risk review hardening for approval/blocking, conservative bounded sizing, and watch-board handoff in manual-first paper mode only. No opaque execution authority and no live trading."
      />

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Prediction intake & execution readiness" title="Risk runtime controls" description="Fortifies prediction→risk→autonomous execution bridge in paper-only, risk-first, approval-aware mode. No live execution.">
          <div className="button-row">
            <button type="button" className="primary-button" disabled={busy} onClick={() => void handleRunRuntime()}>Run intake review</button>
            <button type="button" className="secondary-button" onClick={() => navigate('/opportunity-cycle')}>Open opportunity cycle</button>
            <label>
              Filter status
              <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
                <option value="">All</option>
                <option value="APPROVED">APPROVED</option>
                <option value="APPROVED_REDUCED">APPROVED_REDUCED</option>
                <option value="BLOCKED">BLOCKED</option>
                <option value="NEEDS_REVIEW">NEEDS_REVIEW</option>
              </select>
            </label>
          </div>
          {!runtimeSummary?.latest_run ? (
            <p style={{ marginTop: '0.75rem' }}>No risk runtime decisions are available yet. Run a risk review to evaluate prediction candidates.</p>
          ) : (
            <p style={{ marginTop: '0.75rem' }}>
              Latest run #{runtimeSummary.latest_run.id} · candidates={runtimeSummary.latest_run.candidate_count} · approved={runtimeSummary.latest_run.approved_count} · blocked={runtimeSummary.latest_run.blocked_count}.
            </p>
          )}
        </SectionCard>

        {runtimeSummary?.latest_run ? (
          <SectionCard eyebrow="Runtime summary" title="Paper risk board" description="Auditable summary cards for risk runtime decision quality.">
            <div className="metric-grid">
              <article className="metric-card"><h3>Candidates</h3><strong>{runtimeSummary.latest_run.candidate_count}</strong></article>
              <article className="metric-card"><h3>Handoffs considered</h3><strong>{runtimeSummary.latest_run.considered_handoff_count ?? 0}</strong></article>
              <article className="metric-card"><h3>Approved</h3><strong>{decisionCountByStatus.APPROVED ?? 0}</strong></article>
              <article className="metric-card"><h3>Approved reduced</h3><strong>{decisionCountByStatus.APPROVED_REDUCED ?? 0}</strong></article>
              <article className="metric-card"><h3>Blocked</h3><strong>{decisionCountByStatus.BLOCKED ?? 0}</strong></article>
              <article className="metric-card"><h3>Needs review</h3><strong>{runtimeSummary.latest_run.needs_review_count ?? 0}</strong></article>
              <article className="metric-card"><h3>Watch required</h3><strong>{runtimeSummary.latest_run.watch_required_count}</strong></article>
              <article className="metric-card"><h3>Execution-ready</h3><strong>{runtimeSummary.latest_run.execution_ready_count ?? 0}</strong></article>
            </div>
          </SectionCard>
        ) : null}

        <SectionCard eyebrow="Intake candidates" title="Prediction intake candidates" description="Risk intake status and traceability from risk-ready handoff context.">
          {intakeCandidates.length === 0 ? <EmptyState title="No intake candidates" description="Run intake review to convert prediction handoffs into risk intake candidates." /> : (
            <div className="table-wrapper"><table className="data-table"><thead><tr><th>Market</th><th>Calibrated</th><th>Market</th><th>Edge</th><th>Confidence</th><th>Uncertainty</th><th>Conviction</th><th>Status</th><th>Summary</th></tr></thead><tbody>
              {intakeCandidates.slice(0, 30).map((item) => <tr key={item.id}><td>{item.market_title ?? '—'}</td><td>{item.calibrated_probability}</td><td>{item.market_probability}</td><td>{item.adjusted_edge}</td><td>{item.confidence_score}</td><td>{item.uncertainty_score}</td><td>{item.conviction_bucket || '—'}</td><td><StatusBadge tone={riskTone(item.intake_status)}>{item.intake_status}</StatusBadge></td><td>{item.context_summary}</td></tr>)}
            </tbody></table></div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Runtime decisions" title="Approval decisions" description="Status, score, blockers, and context for each prediction candidate.">
          {approvals.length === 0 ? <EmptyState title="No runtime approval decisions" description="Run risk runtime review to generate explicit risk approvals and blocks." /> : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Market</th><th>Status</th><th>Risk score</th><th>Max exposure</th><th>Blockers</th><th>Links</th></tr></thead>
                <tbody>
                  {approvals.slice(0, 30).map((item) => (
                    <tr key={item.id}>
                      <td>{item.market_title ?? '—'}</td>
                      <td><StatusBadge tone={riskTone(item.approval_status)}>{item.approval_status}</StatusBadge></td>
                      <td>{item.risk_score}</td>
                      <td>{item.max_allowed_exposure}</td>
                      <td>{(item.blockers ?? []).join(', ') || '—'}</td>
                      <td><a href="/prediction">Prediction</a>{' · '}<a href="/execution">Execution sim</a>{' · '}<a href="/trace">Trace</a></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Runtime sizing" title="Sizing plans" description="Bounded Kelly + caps + paper risk budget sizing governance.">
          {sizingPlans.length === 0 ? <EmptyState title="No sizing plans" description="Sizing plans appear after runtime approval decisions are generated." /> : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Market</th><th>Mode</th><th>Raw fraction</th><th>Adjusted fraction</th><th>Cap applied</th><th>Paper notional</th></tr></thead>
                <tbody>
                  {sizingPlans.slice(0, 30).map((item) => (
                    <tr key={item.id}>
                      <td>{item.market_title ?? '—'}</td>
                      <td>{item.sizing_mode}</td>
                      <td>{item.raw_size_fraction}</td>
                      <td>{item.adjusted_size_fraction}</td>
                      <td>{item.cap_applied ? `YES (${(item.cap_reason_codes ?? []).join(', ')})` : 'NO'}</td>
                      <td>{item.paper_notional_size}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Watch board" title="Position watch plans" description="Post-trade watch requirements and escalation paths for position_manager context.">
          {watchPlans.length === 0 ? <EmptyState title="No watch plans" description="Watch plans appear after runtime review decisions." /> : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Market</th><th>Watch status</th><th>Review interval</th><th>Escalation</th><th>Triggers</th></tr></thead>
                <tbody>
                  {watchPlans.slice(0, 30).map((item) => (
                    <tr key={item.id}>
                      <td>{item.market_title ?? '—'}</td>
                      <td><StatusBadge tone={riskTone(item.watch_status)}>{item.watch_status}</StatusBadge></td>
                      <td>{item.review_interval_hint}</td>
                      <td>{item.escalation_path}</td>
                      <td>{Object.keys(item.watch_triggers ?? {}).join(', ') || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Recommendations" title="Runtime recommendations" description="APPROVE/BLOCK/WATCH/EXECUTION_SIM recommendations with rationale and confidence.">
          {runtimeRecommendations.length === 0 ? <EmptyState title="No runtime recommendations" description="Run risk runtime review to produce recommendation-first outputs." /> : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Type</th><th>Market</th><th>Confidence</th><th>Reason codes</th><th>Blockers</th><th>Rationale</th></tr></thead>
                <tbody>
                  {runtimeRecommendations.slice(0, 40).map((item) => (
                    <tr key={item.id}>
                      <td><StatusBadge tone={riskTone(item.recommendation_type.includes('BLOCK') ? 'BLOCKED' : item.recommendation_type.includes('REDUCED') ? 'APPROVED_REDUCED' : 'APPROVED')}>{item.recommendation_type}</StatusBadge></td>
                      <td>{item.market_title ?? '—'}</td>
                      <td>{item.confidence}</td>
                      <td>{(item.reason_codes ?? []).join(', ') || '—'}</td>
                      <td>{(item.blockers ?? []).join(', ') || '—'}</td>
                      <td>{item.rationale}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Autonomous bridge" title="Execution readiness" description="Formal risk→autonomous_trader readiness state for paper-cycle orchestration.">
          {executionReadiness.length === 0 ? <EmptyState title="No readiness records" description="Run intake review to build autonomous execution readiness records." /> : (
            <div className="table-wrapper"><table className="data-table"><thead><tr><th>Market</th><th>Status</th><th>Confidence</th><th>Reason codes</th><th>Summary</th></tr></thead><tbody>
              {executionReadiness.slice(0, 30).map((item) => <tr key={item.id}><td>{item.market_title ?? '—'}</td><td><StatusBadge tone={riskTone(item.readiness_status)}>{item.readiness_status}</StatusBadge></td><td>{item.readiness_confidence}</td><td>{(item.readiness_reason_codes ?? []).join(', ') || '—'}</td><td>{item.readiness_summary}</td></tr>)}
            </tbody></table></div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Legacy controls" title="Assessment + sizing" description="Original risk-agent controls retained for compatibility with existing flows.">
          <div className="button-row">
            <label>Market ID<input value={marketId} onChange={(e) => setMarketId(e.target.value)} placeholder="Optional" /></label>
            <label>Prediction Score ID<input value={predictionId} onChange={(e) => setPredictionId(e.target.value)} placeholder="Optional" /></label>
            <label>Base quantity<input value={baseQuantity} onChange={(e) => setBaseQuantity(e.target.value)} /></label>
            <button type="button" className="secondary-button" disabled={busy} onClick={() => void handleAssess()}>Run assessment</button>
            <button type="button" className="secondary-button" disabled={busy} onClick={() => void handleSize()}>Run sizing</button>
            <button type="button" className="secondary-button" disabled={busy} onClick={() => void handleWatch()}>Run watch loop</button>
          </div>
          {!lastAssessment ? <p style={{ marginTop: '0.75rem' }}>Run a prediction score first when possible, then launch risk assessment.</p> : null}
        </SectionCard>

        <SectionCard eyebrow="Assessment" title="Latest assessment" description="Auditable risk-level summary and key factors.">
          {lastAssessment ? (
            <>
              <p><StatusBadge tone={riskTone(lastAssessment.risk_level)}>{lastAssessment.risk_level}</StatusBadge> · score={lastAssessment.risk_score ?? '—'}</p>
              <p>{lastAssessment.narrative_risk_summary}</p>
              <p>Main factors: {(lastAssessment.key_risk_factors ?? []).slice(0, 4).map((item: any) => item.factor || item.reason).join(', ') || '—'}</p>
            </>
          ) : (
            <EmptyState title="No assessment yet" description="Run assessment to see structured risk factors." />
          )}
        </SectionCard>

        <SectionCard eyebrow="Sizing" title="Latest sizing decision" description="Conservative quantity adjustment under caps and safety pressure.">
          {lastSizing ? (
            <p>base={lastSizing.base_quantity} → adjusted={lastSizing.adjusted_quantity} · mode={lastSizing.sizing_mode} · max_exposure={lastSizing.max_exposure_allowed ?? '—'} · rationale={lastSizing.sizing_rationale}</p>
          ) : (
            <EmptyState title="No sizing decision yet" description="Run sizing after a successful assessment." />
          )}
        </SectionCard>

        <SectionCard eyebrow="Position watch" title="Recent watch events" description="Detect deterioration and emit monitor/caution/review events for open paper positions.">
          {lastWatch?.watched_positions === 0 ? <p>No open positions detected in paper mode.</p> : null}
          {events.length === 0 ? <EmptyState title="No watch events yet" description="Run watch loop to generate monitoring events." /> : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>When</th><th>Market</th><th>Type</th><th>Severity</th><th>Summary</th></tr></thead>
                <tbody>
                  {events.slice(0, 12).map((event) => (
                    <tr key={event.id}>
                      <td>{event.created_at}</td>
                      <td>{event.market_title ?? event.metadata?.market_id ?? '—'}</td>
                      <td>{event.event_type}</td>
                      <td><StatusBadge tone={severityTone(event.severity)}>{event.severity.toUpperCase()}</StatusBadge></td>
                      <td>{event.summary}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <p style={{ marginTop: '0.75rem' }}>Total assessments: {summary?.total_assessments ?? 0} · Total watch events: {summary?.total_watch_events ?? 0}</p>
        </SectionCard>

        <SectionCard eyebrow="History" title="Recent risk assessments" description="Assessment trail with risk levels and sizing linkage for auditability.">
          {assessments.length === 0 ? <EmptyState title="No assessments available" description="Run assess endpoint from this page or from agent pipeline." /> : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Created</th><th>Market</th><th>Risk level</th><th>Score</th><th>Status</th></tr></thead>
                <tbody>
                  {assessments.slice(0, 20).map((item) => (
                    <tr key={item.id}>
                      <td>{item.created_at}</td>
                      <td>{item.market_title ?? item.market ?? '—'}</td>
                      <td><StatusBadge tone={riskTone(item.risk_level)}>{item.risk_level}</StatusBadge></td>
                      <td>{item.risk_score ?? '—'}</td>
                      <td>{item.assessment_status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>
      </DataStateWrapper>
    </div>
  );
}

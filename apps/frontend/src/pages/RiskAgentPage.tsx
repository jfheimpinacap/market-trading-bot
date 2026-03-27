import { useCallback, useEffect, useState } from 'react';
import { EmptyState } from '../components/EmptyState';
import { PageHeader } from '../components/PageHeader';
import { SectionCard } from '../components/SectionCard';
import { StatusBadge } from '../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../components/markets/DataStateWrapper';
import { getRiskAssessments, getRiskSummary, getRiskWatchEvents, runRiskAssessment, runRiskSizing, runRiskWatch } from '../services/riskAgent';

function riskTone(level: string): 'ready' | 'pending' | 'offline' | 'neutral' {
  if (level === 'LOW') return 'ready';
  if (level === 'MEDIUM') return 'pending';
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
      const [summaryRes, assessmentsRes, eventsRes] = await Promise.all([getRiskSummary(), getRiskAssessments(), getRiskWatchEvents()]);
      setSummary(summaryRes);
      setAssessments(assessmentsRes);
      setEvents(eventsRes);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load risk-agent data.');
    } finally {
      setLoading(false);
    }
  }, []);

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

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Risk agent"
        title="Risk Agent"
        description="Structured risk assessment, conservative sizing, and open-position watch loop for paper/demo only. No real-money execution and no real exchange actions."
      />

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Controls" title="Assessment + sizing" description="Run explicit risk assessment between prediction/proposal and allocation.">
          <div className="button-row">
            <label>Market ID<input value={marketId} onChange={(e) => setMarketId(e.target.value)} placeholder="Optional" /></label>
            <label>Prediction Score ID<input value={predictionId} onChange={(e) => setPredictionId(e.target.value)} placeholder="Optional" /></label>
            <label>Base quantity<input value={baseQuantity} onChange={(e) => setBaseQuantity(e.target.value)} /></label>
            <button type="button" className="secondary-button" disabled={busy} onClick={() => void handleAssess()}>Run assessment</button>
            <button type="button" className="secondary-button" disabled={busy} onClick={() => void handleSize()}>Run sizing</button>
            <button type="button" className="primary-button" disabled={busy} onClick={() => void handleWatch()}>Run watch loop</button>
          </div>
          {!lastAssessment ? <p style={{ marginTop: '0.75rem' }}>Run a prediction score first when possible, then launch risk assessment.</p> : null}
        </SectionCard>

        <SectionCard eyebrow="Assessment" title="Latest assessment" description="Auditable risk-level summary and key factors.">
          {lastAssessment ? (
            <>
              <p><StatusBadge tone={riskTone(lastAssessment.risk_level)}>{lastAssessment.risk_level}</StatusBadge> · score={lastAssessment.risk_score ?? '—'}</p>
              <p>{lastAssessment.narrative_risk_summary}</p>
              <p>Main factors: {(lastAssessment.key_risk_factors ?? []).slice(0, 4).map((item: any) => item.factor || item.reason).join(', ') || '—'}</p>
              {lastAssessment.metadata?.precedent_context ? (
                <p>
                  <StatusBadge tone="pending">PRECEDENT_AWARE</StatusBadge>{' '}
                  {String(lastAssessment.metadata.precedent_context.rationale_note ?? 'No strong precedents found for this case.')}
                </p>
              ) : null}
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
          <p style={{ marginBottom: '0.75rem' }}>Need lifecycle actions after watch events? Open <a href="/positions">/positions</a> for hold/reduce/close/review governance.</p>
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
          <p style={{ marginTop: '0.75rem' }}>Total assessments: {summary?.total_assessments ?? 0} · Total watch events: {summary?.total_watch_events ?? 0}</p>
        </SectionCard>
      </DataStateWrapper>
    </div>
  );
}

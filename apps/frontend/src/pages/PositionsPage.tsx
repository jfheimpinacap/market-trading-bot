import { useCallback, useEffect, useMemo, useState } from 'react';
import { EmptyState } from '../components/EmptyState';
import { PageHeader } from '../components/PageHeader';
import { SectionCard } from '../components/SectionCard';
import { StatusBadge } from '../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../components/markets/DataStateWrapper';
import { getPositionDecisions, getPositionLifecycleRuns, getPositionSummary, runPositionLifecycle } from '../services/positions';

function tone(action: string): 'ready' | 'pending' | 'offline' | 'neutral' {
  if (action === 'HOLD') return 'ready';
  if (action === 'REDUCE' || action === 'REVIEW_REQUIRED' || action === 'BLOCK_ADD') return 'pending';
  if (action === 'CLOSE') return 'offline';
  return 'neutral';
}

export function PositionsPage() {
  const [summary, setSummary] = useState<any | null>(null);
  const [runs, setRuns] = useState<any[]>([]);
  const [decisions, setDecisions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryData, runsData, decisionsData] = await Promise.all([
        getPositionSummary(),
        getPositionLifecycleRuns(),
        getPositionDecisions(),
      ]);
      setSummary(summaryData);
      setRuns(runsData);
      setDecisions(decisionsData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load positions lifecycle data.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const counts = useMemo(() => {
    const map = new Map<string, number>();
    for (const row of summary?.status_counts ?? []) map.set(row.status, row.count);
    return {
      hold: map.get('HOLD') ?? 0,
      reduce: map.get('REDUCE') ?? 0,
      close: map.get('CLOSE') ?? 0,
      review: map.get('REVIEW_REQUIRED') ?? 0,
    };
  }, [summary]);

  async function handleRun() {
    setBusy(true);
    setError(null);
    try {
      await runPositionLifecycle({ metadata: { triggered_from: 'positions_page' } });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Lifecycle run failed.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Position lifecycle"
        title="Positions"
        description="Holding governance for open paper positions: decide hold/reduce/close/review with explicit rationale, runtime/safety guardrails, and fully auditable paper-only exit plans."
      />

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Lifecycle controls" title="Run lifecycle review" description="Evaluate open paper positions and transform watch events into operational decisions.">
          <div className="button-row">
            <button type="button" className="primary-button" disabled={busy} onClick={() => void handleRun()}>Run lifecycle review</button>
            <p>Execution mode: <strong>paper/demo only</strong>. No real-money execution.</p>
          </div>
        </SectionCard>

        <section className="stats-grid">
          <article className="status-card"><p className="status-card__label">Hold</p><p className="status-card__value">{counts.hold}</p></article>
          <article className="status-card"><p className="status-card__label">Reduce</p><p className="status-card__value">{counts.reduce}</p></article>
          <article className="status-card"><p className="status-card__label">Close</p><p className="status-card__value">{counts.close}</p></article>
          <article className="status-card"><p className="status-card__label">Review required</p><p className="status-card__value">{counts.review}</p></article>
        </section>

        <SectionCard eyebrow="Decisions" title="Position lifecycle table" description="Latest decision per position with execution path and rationale.">
          {decisions.length === 0 ? <EmptyState title="No open paper positions to review right now." description="Run lifecycle review after opening at least one paper position." /> : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Market</th><th>PnL</th><th>Edge</th><th>Watch</th><th>Action</th><th>Rationale</th><th>Execution path</th></tr></thead>
                <tbody>
                  {decisions.slice(0, 40).map((item) => (
                    <tr key={item.id}>
                      <td>{item.market_title ?? '—'}</td>
                      <td>{item.position_snapshot?.pnl_unrealized ?? '—'}</td>
                      <td>{item.position_snapshot?.current_edge_estimate ?? '—'}</td>
                      <td>{item.position_snapshot?.watch_severity ?? '—'}</td>
                      <td><StatusBadge tone={tone(item.status)}>{item.status}</StatusBadge></td>
                      <td>{item.rationale}</td>
                      <td>{item.exit_plan?.execution_path ?? 'record_only'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Runs" title="Recent lifecycle runs" description="Operational run history and action mix per run.">
          {runs.length === 0 ? <EmptyState title="No lifecycle runs yet" description="Run the lifecycle control to generate the first governance run." /> : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Created</th><th>Status</th><th>Positions</th><th>Close/Reduce/Review</th><th>Summary</th></tr></thead>
                <tbody>
                  {runs.slice(0, 20).map((run) => (
                    <tr key={run.id}>
                      <td>{run.created_at}</td>
                      <td>{run.status}</td>
                      <td>{run.watched_positions}</td>
                      <td>{run.close_count}/{run.reduce_count}/{run.review_required_count}</td>
                      <td>{run.summary}</td>
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

import { useCallback, useEffect, useMemo, useState } from 'react';
import { EmptyState } from '../../components/EmptyState';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { navigate } from '../../lib/router';
import { getReplayRunSteps, getReplayRuns, getReplaySummary, runReplay } from '../../services/replay';
import type { ReplayRun, ReplayStep, RunReplayPayload } from '../../types/replay';

const defaultForm: RunReplayPayload = {
  provider_scope: 'all',
  source_scope: 'real_only',
  start_timestamp: new Date(Date.now() - 7 * 24 * 3600 * 1000).toISOString(),
  end_timestamp: new Date().toISOString(),
  market_limit: 8,
  active_only: true,
  use_allocation: true,
  use_learning_adjustments: true,
  auto_execute_allowed: true,
  treat_approval_required_as_skip: true,
  stop_on_error: false,
  execution_mode: 'naive',
  execution_profile: 'balanced_paper',
};

function tone(status: string) {
  if (status === 'SUCCESS' || status === 'READY') return 'ready';
  if (status === 'FAILED') return 'offline';
  if (status === 'PARTIAL') return 'pending';
  return 'neutral';
}

const money = (value?: string) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(Number(value ?? 0));

export function ReplayPage() {
  const [runs, setRuns] = useState<ReplayRun[]>([]);
  const [lastRun, setLastRun] = useState<ReplayRun | null>(null);
  const [steps, setSteps] = useState<ReplayStep[]>([]);
  const [form, setForm] = useState<RunReplayPayload>(defaultForm);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [summary, recent] = await Promise.all([getReplaySummary(), getReplayRuns()]);
      setRuns(recent);
      setLastRun(summary.latest_run);
      if (summary.latest_run?.id) {
        setSteps(await getReplayRunSteps(summary.latest_run.id));
      } else {
        setSteps([]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load replay data.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function submitReplay() {
    setBusy(true);
    setError(null);
    try {
      await runReplay(form);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Replay execution failed. Sync real market data first to build a usable historical replay.');
    } finally {
      setBusy(false);
    }
  }

  const runRange = useMemo(() => {
    if (!lastRun) return '—';
    return `${new Date(lastRun.replay_start_at).toLocaleString()} → ${new Date(lastRun.replay_end_at).toLocaleString()}`;
  }, [lastRun]);
  const latestImpact = lastRun?.details?.execution_impact_summary;

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Historical replay / backtest-like demo"
        title="Replay"
        description="Historical replay uses persisted snapshots in paper/demo mode only. It does not connect to live execution or real money."
        actions={<div className="button-row"><button type="button" className="secondary-button" onClick={() => navigate('/evaluation')}>Open Evaluation</button><button type="button" className="secondary-button" onClick={() => navigate('/experiments')}>Open Experiments</button><button type="button" className="secondary-button" onClick={() => navigate('/continuous-demo')}>Open Continuous Demo</button></div>}
      />

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Replay control panel" title="Run historical replay" description="Select replay scope and execute using stored snapshots.">
          <div className="system-metadata-grid">
            <label>Provider scope <input value={form.provider_scope} onChange={(e) => setForm((prev) => ({ ...prev, provider_scope: e.target.value }))} /></label>
            <label>Source scope <select value={form.source_scope} onChange={(e) => setForm((prev) => ({ ...prev, source_scope: e.target.value as RunReplayPayload['source_scope'] }))}><option value="real_only">real_only</option><option value="demo_only">demo_only</option><option value="mixed">mixed</option></select></label>
            <label>Start <input type="datetime-local" onChange={(e) => setForm((prev) => ({ ...prev, start_timestamp: new Date(e.target.value).toISOString() }))} /></label>
            <label>End <input type="datetime-local" onChange={(e) => setForm((prev) => ({ ...prev, end_timestamp: new Date(e.target.value).toISOString() }))} /></label>
            <label>Market limit <input type="number" value={form.market_limit} onChange={(e) => setForm((prev) => ({ ...prev, market_limit: Number(e.target.value) }))} /></label>
            <label>Execution mode <select value={form.execution_mode} onChange={(e) => setForm((prev) => ({ ...prev, execution_mode: e.target.value as RunReplayPayload['execution_mode'] }))}><option value="naive">naive</option><option value="execution_aware">execution_aware</option></select></label>
            <label>Execution profile <select value={form.execution_profile} onChange={(e) => setForm((prev) => ({ ...prev, execution_profile: e.target.value as RunReplayPayload['execution_profile'] }))}><option value="optimistic_paper">optimistic_paper</option><option value="balanced_paper">balanced_paper</option><option value="conservative_paper">conservative_paper</option></select></label>
          </div>
          <div className="button-row" style={{ marginTop: '1rem' }}>
            <button type="button" className="primary-button" disabled={busy} onClick={() => void submitReplay()}>{busy ? 'Running replay…' : 'Execute replay'}</button>
          </div>
        </SectionCard>

        {!lastRun ? (
          <EmptyState eyebrow="No replay runs" title="No replay runs yet." description="Sync real market data first to build a usable historical replay." />
        ) : (
          <>
            <SectionCard eyebrow="Last run summary" title="Latest replay result" description="Top-level metrics for quick comparison.">
              <div className="system-metadata-grid">
                <div><strong>Status:</strong> <StatusBadge tone={tone(lastRun.status)}>{lastRun.status}</StatusBadge></div>
                <div><strong>Range:</strong> {runRange}</div>
                <div><strong>Proposals:</strong> {lastRun.proposals_generated}</div>
                <div><strong>Trades:</strong> {lastRun.trades_executed}</div>
                <div><strong>Approval-required:</strong> {lastRun.approvals_required}</div>
                <div><strong>Blocked:</strong> {lastRun.blocked_count}</div>
                <div><strong>Total PnL:</strong> {money(lastRun.total_pnl)}</div>
                <div><strong>Ending equity:</strong> {money(lastRun.ending_equity)}</div>
                <div><strong>Mode:</strong> {lastRun.details?.execution_mode ?? 'naive'}</div>
                <div><strong>Profile:</strong> {lastRun.details?.execution_profile ?? '—'}</div>
              </div>
              {lastRun.details?.execution_mode === 'execution_aware' ? (
                <div className="system-metadata-grid" style={{ marginTop: '1rem' }}>
                  <div><strong>Fill rate:</strong> {((latestImpact?.fill_rate ?? 0) * 100).toFixed(2)}%</div>
                  <div><strong>No-fill rate:</strong> {((latestImpact?.no_fill_rate ?? 0) * 100).toFixed(2)}%</div>
                  <div><strong>Partial-fill rate:</strong> {((latestImpact?.partial_fill_rate ?? 0) * 100).toFixed(2)}%</div>
                  <div><strong>Avg slippage:</strong> {latestImpact?.avg_slippage_bps ?? 0} bps</div>
                  <div><strong>Execution-adjusted PnL:</strong> {money(latestImpact?.execution_adjusted_pnl)}</div>
                  <div><strong>Execution drag:</strong> {money(latestImpact?.execution_drag)}</div>
                </div>
              ) : (
                <p style={{ marginTop: '1rem' }}>Run replay with execution-aware mode to measure fill realism.</p>
              )}
            </SectionCard>

            <SectionCard eyebrow="Recent replay runs" title="Run history" description="Auditable replay runs for side-by-side checks with evaluation metrics.">
              <div className="table-wrapper">
                <table className="data-table">
                  <thead><tr><th>ID</th><th>Status</th><th>Provider</th><th>Time range</th><th>Trades</th><th>PnL</th><th>Created</th></tr></thead>
                  <tbody>
                    {runs.map((run) => (
                      <tr key={run.id}>
                        <td>{run.id}</td>
                        <td><StatusBadge tone={tone(run.status)}>{run.status}</StatusBadge></td>
                        <td>{run.provider_scope}</td>
                        <td>{new Date(run.replay_start_at).toLocaleDateString()} - {new Date(run.replay_end_at).toLocaleDateString()}</td>
                        <td>{run.trades_executed}</td>
                        <td>{money(run.total_pnl)}</td>
                        <td>{new Date(run.created_at).toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </SectionCard>

            <SectionCard eyebrow="Run detail" title="Timeline steps" description="Step-level replay summary for audit and debugging.">
              <div className="table-wrapper">
                <table className="data-table">
                  <thead><tr><th>Step</th><th>Timestamp</th><th>Snapshots</th><th>Proposals</th><th>Trades</th><th>Blocked</th><th>Equity</th><th>Notes</th></tr></thead>
                  <tbody>
                    {steps.map((step) => (
                      <tr key={step.id}>
                        <td>{step.step_index}</td>
                        <td>{new Date(step.step_timestamp).toLocaleString()}</td>
                        <td>{step.snapshots_used}</td>
                        <td>{step.proposals_generated}</td>
                        <td>{step.trades_executed}</td>
                        <td>{step.blocked_count}</td>
                        <td>{money(step.estimated_equity)}</td>
                        <td>{step.notes}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </SectionCard>
          </>
        )}
      </DataStateWrapper>
    </div>
  );
}

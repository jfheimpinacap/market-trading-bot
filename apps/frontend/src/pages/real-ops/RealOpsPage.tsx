import { useCallback, useEffect, useState } from 'react';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { navigate } from '../../lib/router';
import { evaluateRealMarketOps, getRealMarketOpRuns, getRealMarketOpStatus, runRealMarketOps } from '../../services/realOps';
import type { RealMarketOpRun, RealMarketOpsEvaluateResponse, RealMarketOpsStatus } from '../../types/realOps';

export function RealOpsPage() {
  const [status, setStatus] = useState<RealMarketOpsStatus | null>(null);
  const [evaluation, setEvaluation] = useState<RealMarketOpsEvaluateResponse | null>(null);
  const [runs, setRuns] = useState<RealMarketOpRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [statusResponse, runsResponse] = await Promise.all([getRealMarketOpStatus(), getRealMarketOpRuns(12)]);
      setStatus(statusResponse);
      setRuns(runsResponse);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load real ops state.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleEvaluate() {
    setBusy(true);
    try {
      setEvaluation(await evaluateRealMarketOps());
      await load();
    } finally {
      setBusy(false);
    }
  }

  async function handleRun() {
    setBusy(true);
    try {
      await runRealMarketOps('manual');
      await load();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Autonomous real-market scope"
        title="Real Ops"
        description="Autonomous evaluation and paper execution only for eligible real markets in read-only data mode. No real exchange auth. No real money execution."
        actions={<div className="button-row"><button type="button" className="secondary-button" onClick={() => navigate('/allocation')}>Open Allocation</button><button type="button" className="secondary-button" onClick={() => navigate('/continuous-demo')}>Open Continuous Demo</button></div>}
      />

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Safety envelope" title="Scope and execution constraints" description="This mode only works on real_read_only sources with paper_demo_only execution.">
          <div className="button-row">
            <StatusBadge tone="ready">REAL</StatusBadge>
            <StatusBadge tone="pending">READ-ONLY</StatusBadge>
            <StatusBadge tone="neutral">PAPER ONLY</StatusBadge>
            <StatusBadge tone={status?.enabled ? 'ready' : 'offline'}>{status?.enabled ? 'ENABLED' : 'DISABLED'}</StatusBadge>
          </div>
          <ul>
            <li>Provider scope: {String(status?.scope?.provider_scope ?? '—')}</li>
            <li>Stale data blocks execution: {String(status?.scope?.stale_data_blocks_execution ?? '—')}</li>
            <li>Degraded provider blocks execution: {String(status?.scope?.degraded_provider_blocks_execution ?? '—')}</li>
            <li>Max real markets/cycle: {String(status?.scope?.max_real_markets_per_cycle ?? '—')}</li>
            <li>Max real auto trades/cycle: {String(status?.scope?.max_real_auto_trades_per_cycle ?? '—')}</li>
            <li>Min liquidity/volume: {String(status?.scope?.min_liquidity_threshold ?? '0')} / {String(status?.scope?.min_volume_threshold ?? '0')}</li>
          </ul>
        </SectionCard>

        <SectionCard eyebrow="Control panel" title="Evaluate or run" description="Evaluate eligibility before running autonomous paper-only cycle.">
          <div className="button-row">
            <button type="button" className="secondary-button" disabled={busy} onClick={() => void handleEvaluate()}>Evaluate real-market scope</button>
            <button type="button" className="primary-button" disabled={busy || !status?.enabled} onClick={() => void handleRun()}>Run real-market paper cycle</button>
          </div>
        </SectionCard>

        <SectionCard eyebrow="Allocation bridge" title="Execution prioritization status" description="Real Ops uses allocation prioritization before paper auto-execution when multiple proposals compete.">
          <div className="button-row">
            <StatusBadge tone="ready">ALLOCATION ACTIVE</StatusBadge>
            <StatusBadge tone="neutral">PAPER/DEMO ONLY</StatusBadge>
          </div>
        </SectionCard>

        <SectionCard eyebrow="Eligibility" title="Eligible markets snapshot" description="Eligibility enforces provider freshness, pricing sufficiency, and conservative thresholds.">
          <p>
            Considered: {evaluation?.markets_considered ?? 0} · Eligible: {evaluation?.markets_eligible ?? 0} · Excluded: {evaluation?.excluded_count ?? 0}
          </p>
          <p>
            Skipped stale: {evaluation?.skipped_stale_count ?? 0} · Skipped degraded: {evaluation?.skipped_degraded_provider_count ?? 0} · Skipped no pricing: {evaluation?.skipped_no_pricing_count ?? 0}
          </p>
        </SectionCard>

        <SectionCard eyebrow="Recent runs" title="Real-market operation runs" description="Auditable run history for autonomous real-scope paper operations.">
          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr><th>ID</th><th>Status</th><th>Providers</th><th>Considered</th><th>Eligible</th><th>Auto</th><th>Approvals</th><th>Blocked</th><th>Skipped stale/degraded/no pricing</th></tr>
              </thead>
              <tbody>
                {runs.map((run) => (
                  <tr key={run.id}>
                    <td>{run.id}</td>
                    <td><StatusBadge tone={run.status === 'SUCCESS' ? 'ready' : run.status === 'FAILED' ? 'offline' : 'pending'}>{run.status}</StatusBadge></td>
                    <td>{run.providers_considered}</td>
                    <td>{run.markets_considered}</td>
                    <td>{run.markets_eligible}</td>
                    <td>{run.auto_executed_count}</td>
                    <td>{run.approval_required_count}</td>
                    <td>{run.blocked_count}</td>
                    <td>{run.skipped_stale_count}/{run.skipped_degraded_provider_count}/{run.skipped_no_pricing_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionCard>
      </DataStateWrapper>
    </div>
  );
}

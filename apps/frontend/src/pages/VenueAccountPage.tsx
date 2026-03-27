import { useCallback, useEffect, useMemo, useState } from 'react';

import { EmptyState } from '../components/EmptyState';
import { PageHeader } from '../components/PageHeader';
import { SectionCard } from '../components/SectionCard';
import { StatusBadge } from '../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../components/markets/DataStateWrapper';
import { navigate } from '../lib/router';
import {
  getVenueAccountBalances,
  getVenueAccountCurrent,
  getVenueAccountOrders,
  getVenueAccountPositions,
  getVenueAccountSummary,
  getVenueReconciliationRuns,
  runVenueReconciliation,
} from '../services/venueAccount';
import type { VenueAccountSnapshot, VenueAccountSummary, VenueBalanceSnapshot, VenueOrderSnapshot, VenuePositionSnapshot, VenueReconciliationRun } from '../types/venueAccount';

const STATUS_TONE: Record<string, 'ready' | 'pending' | 'offline' | 'neutral'> = {
  SANDBOX_ONLY: 'pending',
  PARITY_OK: 'ready',
  PARITY_GAP: 'pending',
  STATUS_MISMATCH: 'pending',
  BALANCE_DRIFT: 'offline',
};

export function VenueAccountPage() {
  const [current, setCurrent] = useState<VenueAccountSnapshot | null>(null);
  const [orders, setOrders] = useState<VenueOrderSnapshot[]>([]);
  const [positions, setPositions] = useState<VenuePositionSnapshot[]>([]);
  const [balances, setBalances] = useState<VenueBalanceSnapshot[]>([]);
  const [runs, setRuns] = useState<VenueReconciliationRun[]>([]);
  const [summary, setSummary] = useState<VenueAccountSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [currentData, orderData, positionData, balanceData, runData, summaryData] = await Promise.all([
        getVenueAccountCurrent(),
        getVenueAccountOrders(),
        getVenueAccountPositions(),
        getVenueAccountBalances(),
        getVenueReconciliationRuns(),
        getVenueAccountSummary(),
      ]);
      setCurrent(currentData);
      setOrders(orderData);
      setPositions(positionData);
      setBalances(balanceData);
      setRuns(runData);
      setSummary(summaryData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load venue account mirror data.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleRunReconciliation() {
    setBusy(true);
    setError(null);
    try {
      await runVenueReconciliation({ metadata: { triggered_from: 'venue_account_page' } });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not run reconciliation.');
    } finally {
      setBusy(false);
    }
  }

  const latestRun = useMemo(() => runs[0] ?? null, [runs]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="External state parity"
        title="Venue Account Mirror"
        description="Sandbox-only external account/order/position mirror and reconciliation layer. No real credentials, no live account connectivity, no real execution."
        actions={<div className="button-row"><button type="button" className="secondary-button" onClick={() => navigate('/trace')}>Open Trace Explorer</button></div>}
      />

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Safety boundary" title="Incoming external bridge is sandbox only" description="This mirror represents how a broker/venue account could look, while remaining fully local-first and non-live.">
          <p>
            <StatusBadge tone="pending">SANDBOX_ONLY</StatusBadge> · parity:{' '}
            <StatusBadge tone={STATUS_TONE[latestRun?.status ?? 'PARITY_GAP'] ?? 'neutral'}>{latestRun?.status ?? 'PARITY_GAP'}</StatusBadge>
          </p>
          <p>
            Build outgoing payload parity first in <a href="/execution-venue">Execution Venue</a>, then inspect incoming state parity here. Run adapter certification in <a href="/connectors">Connectors</a>. Final readiness remains in <a href="/go-live">Go-Live Gate</a>.
          </p>
        </SectionCard>

        <SectionCard eyebrow="Account snapshot" title="Current external-style account state" description="Canonical snapshot of venue-style account metrics.">
          {!current ? (
            <EmptyState title="No account snapshot yet." description="Create broker intents and venue dry-runs first to build a sandbox account mirror." />
          ) : (
            <div className="stats-grid">
              <article className="status-card"><p className="status-card__label">Venue</p><p className="status-card__value">{current.venue_name}</p></article>
              <article className="status-card"><p className="status-card__label">Mode</p><p className="status-card__value">{current.account_mode}</p></article>
              <article className="status-card"><p className="status-card__label">Equity</p><p className="status-card__value">{current.equity}</p></article>
              <article className="status-card"><p className="status-card__label">Cash available</p><p className="status-card__value">{current.cash_available}</p></article>
              <article className="status-card"><p className="status-card__label">Reserved cash</p><p className="status-card__value">{current.reserved_cash}</p></article>
              <article className="status-card"><p className="status-card__label">Open positions / orders</p><p className="status-card__value">{current.open_positions_count} / {current.open_orders_count}</p></article>
            </div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Orders" title="External order snapshots" description="Canonical view of sandbox external orders derived from intents + responses + paper fills.">
          {orders.length === 0 ? (
            <EmptyState title="No external order snapshots yet." description="Create broker intents and venue dry-runs first to build a sandbox account mirror." />
          ) : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>External order</th><th>Source intent</th><th>Instrument</th><th>Qty/Filled/Remaining</th><th>Status</th><th>Updated</th></tr></thead>
                <tbody>
                  {orders.map((order) => (
                    <tr key={order.id}>
                      <td>{order.external_order_id}</td>
                      <td>{order.source_intent_ref_id ?? '—'}</td>
                      <td>{order.instrument_ref}</td>
                      <td>{order.quantity} / {order.filled_quantity} / {order.remaining_quantity}</td>
                      <td><StatusBadge tone={STATUS_TONE[order.status] ?? 'neutral'}>{order.status}</StatusBadge></td>
                      <td>{order.updated_at}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Positions" title="External position snapshots" description="Canonical view of sandbox external positions mapped from internal portfolio positions.">
          {positions.length === 0 ? (
            <EmptyState title="No external position snapshots yet." description="Create paper positions first, then rebuild mirror by running reconciliation." />
          ) : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Instrument</th><th>Qty</th><th>Avg entry</th><th>Unrealized PnL</th><th>Source internal position</th><th>Status</th></tr></thead>
                <tbody>
                  {positions.map((position) => (
                    <tr key={position.id}>
                      <td>{position.external_instrument_ref}</td>
                      <td>{position.quantity}</td>
                      <td>{position.avg_entry_price}</td>
                      <td>{position.unrealized_pnl ?? '—'}</td>
                      <td>{position.source_internal_position ?? '—'}</td>
                      <td><StatusBadge tone={position.status === 'OPEN' ? 'ready' : 'neutral'}>{position.status}</StatusBadge></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Balances + reconciliation" title="Parity diagnostics" description="Run reconciliation and inspect mismatches/issues as valid outcomes, not system errors.">
          <div className="button-row">
            <button type="button" className="primary-button" onClick={() => void handleRunReconciliation()} disabled={busy}>Run reconciliation</button>
          </div>
          <p>
            Latest parity:{' '}
            <StatusBadge tone={STATUS_TONE[summary?.latest_reconciliation?.status ?? 'PARITY_GAP'] ?? 'neutral'}>
              {summary?.latest_reconciliation?.status ?? 'PARITY_GAP'}
            </StatusBadge>{' '}
            · mismatches: {summary?.latest_reconciliation?.mismatches_count ?? 0}
          </p>
          <p><strong>Balances:</strong> {balances.map((balance) => `${balance.currency} ${balance.total} (available ${balance.available}, reserved ${balance.reserved})`).join(' · ') || 'none'}</p>

          {runs.length === 0 ? (
            <EmptyState title="No reconciliation runs yet." description="Run reconciliation to compare internal paper state against the external mirror state." />
          ) : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Run</th><th>Status</th><th>Compared (O/P/B)</th><th>Mismatches</th><th>Summary</th><th>Created</th></tr></thead>
                <tbody>
                  {runs.slice(0, 10).map((run) => (
                    <tr key={run.id}>
                      <td>#{run.id}</td>
                      <td><StatusBadge tone={STATUS_TONE[run.status] ?? 'neutral'}>{run.status}</StatusBadge></td>
                      <td>{run.orders_compared}/{run.positions_compared}/{run.balances_compared}</td>
                      <td>{run.mismatches_count}</td>
                      <td>{run.summary}</td>
                      <td>{run.created_at}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="stack-sm">
            <p><strong>Recent issues:</strong></p>
            {summary?.recent_issues?.length ? (
              summary.recent_issues.slice(0, 5).map((issue) => (
                <p key={issue.id}><StatusBadge tone={issue.issue_type === 'balance_drift' ? 'offline' : 'pending'}>{issue.issue_type.toUpperCase()}</StatusBadge> · {issue.reason}</p>
              ))
            ) : (
              <p>No recent issues.</p>
            )}
          </div>
        </SectionCard>
      </DataStateWrapper>
    </div>
  );
}

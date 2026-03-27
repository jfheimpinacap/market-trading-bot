import { useCallback, useEffect, useMemo, useState } from 'react';

import { EmptyState } from '../components/EmptyState';
import { PageHeader } from '../components/PageHeader';
import { SectionCard } from '../components/SectionCard';
import { StatusBadge } from '../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../components/markets/DataStateWrapper';
import { createPaperOrder, getExecutionSummary, getPaperFills, getPaperOrders, runExecutionLifecycle } from '../services/execution';
import { getMarkets } from '../services/markets';
import { navigate } from '../lib/router';

const TONE: Record<string, 'ready' | 'pending' | 'offline' | 'neutral'> = {
  OPEN: 'pending',
  PARTIALLY_FILLED: 'pending',
  FILLED: 'ready',
  CANCELLED: 'offline',
  EXPIRED: 'offline',
  REJECTED: 'offline',
};

export function ExecutionPage() {
  const [summary, setSummary] = useState<any | null>(null);
  const [orders, setOrders] = useState<any[]>([]);
  const [fills, setFills] = useState<any[]>([]);
  const [markets, setMarkets] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryData, ordersData, fillsData, marketsData] = await Promise.all([
        getExecutionSummary(),
        getPaperOrders(),
        getPaperFills(),
        getMarkets(),
      ]);
      setSummary(summaryData);
      setOrders(ordersData);
      setFills(fillsData);
      setMarkets(marketsData.slice(0, 20));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load execution simulator data.');
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
      open: map.get('OPEN') ?? 0,
      partial: map.get('PARTIALLY_FILLED') ?? 0,
      filled: map.get('FILLED') ?? 0,
      cancelledExpired: (map.get('CANCELLED') ?? 0) + (map.get('EXPIRED') ?? 0),
      rejected: map.get('REJECTED') ?? 0,
    };
  }, [summary]);

  async function handleLifecycle() {
    setBusy(true);
    setError(null);
    try {
      await runExecutionLifecycle({ open_only: true, metadata: { triggered_from: 'execution_page' } });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Lifecycle run failed.');
    } finally {
      setBusy(false);
    }
  }

  async function handleCreateTestOrder() {
    if (!markets.length) return;
    setBusy(true);
    setError(null);
    try {
      await createPaperOrder({
        market_id: markets[0].id,
        side: 'BUY_YES',
        requested_quantity: '1.0000',
        created_from: 'manual',
        policy_profile: 'balanced_paper',
        metadata: { triggered_from: 'execution_page' },
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create test order.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Execution simulator"
        title="Execution"
        description="Paper/demo-only order lifecycle simulator that separates trade intent from realistic execution outcomes: full fill, partial fill, no fill, cancellation, or expiration."
        actions={<div className="button-row"><button type="button" className="secondary-button" onClick={() => navigate('/broker-bridge')}>Open Broker Bridge</button></div>}
      />

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Lifecycle controls" title="Review pending paper orders" description="Run a formal lifecycle pass to re-evaluate open/partial orders using conservative paper execution realism rules.">
          <div className="button-row">
            <button type="button" className="primary-button" disabled={busy} onClick={() => void handleLifecycle()}>Run order lifecycle review</button>
            <button type="button" className="secondary-button" disabled={busy || !markets.length} onClick={() => void handleCreateTestOrder()}>Create test order</button>
            <p><strong>Paper/demo only.</strong> No real-money routing or exchange execution.</p>
          </div>
        </SectionCard>

        <section className="stats-grid">
          <article className="status-card"><p className="status-card__label">Open orders</p><p className="status-card__value">{counts.open}</p></article>
          <article className="status-card"><p className="status-card__label">Partially filled</p><p className="status-card__value">{counts.partial}</p></article>
          <article className="status-card"><p className="status-card__label">Filled</p><p className="status-card__value">{counts.filled}</p></article>
          <article className="status-card"><p className="status-card__label">Cancelled / expired</p><p className="status-card__value">{counts.cancelledExpired}</p></article>
          <article className="status-card"><p className="status-card__label">Rejected</p><p className="status-card__value">{counts.rejected}</p></article>
        </section>

        <SectionCard eyebrow="Orders" title="Paper orders" description="Trade intents transformed into realistic execution lifecycle states.">
          {orders.length === 0 ? (
            <EmptyState title="No paper orders created yet." description="Create a test order or run opportunity/position cycles to generate paper orders." />
          ) : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Market</th><th>Side</th><th>Requested qty</th><th>Remaining qty</th><th>Status</th><th>Requested price</th><th>Effective price</th><th>Created from</th><th>Created at</th></tr></thead>
                <tbody>
                  {orders.slice(0, 60).map((order) => (
                    <tr key={order.id}>
                      <td>{order.market_title ?? order.market}</td>
                      <td>{order.side}</td>
                      <td>{order.requested_quantity}</td>
                      <td>{order.remaining_quantity}</td>
                      <td><StatusBadge tone={TONE[order.status] ?? 'neutral'}>{order.status}</StatusBadge></td>
                      <td>{order.requested_price ?? '—'}</td>
                      <td>{order.effective_price ?? '—'}</td>
                      <td>{order.created_from}</td>
                      <td>{order.created_at}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Fills" title="Paper fills" description="Explicit fill records from lifecycle execution attempts.">
          {fills.length === 0 ? (
            <EmptyState title="No fills yet." description="No fill is also a valid operational result under low-liquidity or stale/degraded conditions." />
          ) : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Order</th><th>Quantity</th><th>Fill price</th><th>Fill type</th><th>Created at</th></tr></thead>
                <tbody>
                  {fills.slice(0, 80).map((fill) => (
                    <tr key={fill.id}>
                      <td>#{fill.paper_order}</td>
                      <td>{fill.fill_quantity}</td>
                      <td>{fill.fill_price}</td>
                      <td>{fill.fill_type}</td>
                      <td>{fill.created_at}</td>
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

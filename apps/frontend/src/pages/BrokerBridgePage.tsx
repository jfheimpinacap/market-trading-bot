import { useCallback, useEffect, useMemo, useState } from 'react';

import { EmptyState } from '../components/EmptyState';
import { PageHeader } from '../components/PageHeader';
import { SectionCard } from '../components/SectionCard';
import { StatusBadge } from '../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../components/markets/DataStateWrapper';
import { createBrokerIntent, dryRunBrokerIntent, getBrokerBridgeSummary, getBrokerIntents, validateBrokerIntent } from '../services/brokerBridge';
import { getPaperOrders } from '../services/execution';
import type { BrokerOrderIntent } from '../types/brokerBridge';

const STATUS_TONE: Record<string, 'ready' | 'pending' | 'offline' | 'neutral'> = {
  DRAFT: 'neutral',
  VALIDATED: 'pending',
  REJECTED: 'offline',
  DRY_RUN_READY: 'pending',
  DRY_RUN_EXECUTED: 'ready',
  accepted: 'ready',
  rejected: 'offline',
  hold: 'pending',
  needs_manual_review: 'pending',
};

export function BrokerBridgePage() {
  const [summary, setSummary] = useState<any | null>(null);
  const [intents, setIntents] = useState<BrokerOrderIntent[]>([]);
  const [paperOrders, setPaperOrders] = useState<any[]>([]);
  const [selectedIntentId, setSelectedIntentId] = useState<number | null>(null);
  const [selectedSourceOrderId, setSelectedSourceOrderId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryData, intentsData, paperOrdersData] = await Promise.all([getBrokerBridgeSummary(), getBrokerIntents(), getPaperOrders()]);
      setSummary(summaryData);
      setIntents(intentsData);
      setPaperOrders(paperOrdersData);
      setSelectedIntentId((prev) => prev ?? intentsData[0]?.id ?? null);
      setSelectedSourceOrderId((prev) => prev ?? paperOrdersData[0]?.id ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load broker bridge state.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const selectedIntent = useMemo(() => intents.find((intent) => intent.id === selectedIntentId) ?? null, [intents, selectedIntentId]);

  async function handleCreateIntent() {
    if (!selectedSourceOrderId) return;
    setBusy(true);
    setError(null);
    try {
      await createBrokerIntent({ source_type: 'paper_order', source_id: String(selectedSourceOrderId), payload: { metadata: { triggered_from: 'broker_bridge_page' } } });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create broker intent.');
    } finally {
      setBusy(false);
    }
  }

  async function handleValidate(intentId: number) {
    setBusy(true);
    setError(null);
    try {
      await validateBrokerIntent(intentId, { metadata: { triggered_from: 'broker_bridge_page' } });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not validate intent.');
    } finally {
      setBusy(false);
    }
  }

  async function handleDryRun(intentId: number) {
    setBusy(true);
    setError(null);
    try {
      await dryRunBrokerIntent(intentId, { metadata: { triggered_from: 'broker_bridge_page' } });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not run dry-run router.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Broker bridge sandbox"
        title="Broker Bridge"
        description="Paper-only bridge that translates internal execution decisions into broker-like order intents, validates readiness guardrails, and runs sandbox dry-run routing."
      />

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard
          eyebrow="Paper-only boundary"
          title="Dry-run order router controls"
          description="This module never sends real orders. It only records what would be routed to a future broker connector under current certification/runtime/safety constraints."
        >
          <p>Need final pre-live controls? Open the <a href="/go-live">Go-Live Gate</a> for checklist, approvals, and capital firewall status. Need canonical adapter parity? Open <a href="/execution-venue">Execution Venue</a>.</p>
          <div className="button-row">
            <select value={selectedSourceOrderId ?? ''} onChange={(event) => setSelectedSourceOrderId(Number(event.target.value))}>
              {paperOrders.map((order) => (
                <option key={order.id} value={order.id}>Paper Order #{order.id} · {order.market_title} · {order.side}</option>
              ))}
            </select>
            <button type="button" className="primary-button" disabled={busy || !selectedSourceOrderId} onClick={() => void handleCreateIntent()}>Create intent from paper order</button>
            {selectedIntent ? <button type="button" className="secondary-button" disabled={busy} onClick={() => void handleValidate(selectedIntent.id)}>Validate selected intent</button> : null}
            {selectedIntent ? <button type="button" className="secondary-button" disabled={busy} onClick={() => void handleDryRun(selectedIntent.id)}>Run dry-run for selected intent</button> : null}
          </div>
        </SectionCard>

        <section className="stats-grid">
          <article className="status-card"><p className="status-card__label">Intents created</p><p className="status-card__value">{summary?.intents_created ?? 0}</p></article>
          <article className="status-card"><p className="status-card__label">Validated</p><p className="status-card__value">{summary?.validated ?? 0}</p></article>
          <article className="status-card"><p className="status-card__label">Rejected</p><p className="status-card__value">{summary?.rejected ?? 0}</p></article>
          <article className="status-card"><p className="status-card__label">Dry-run accepted</p><p className="status-card__value">{summary?.dry_run_accepted ?? 0}</p></article>
          <article className="status-card"><p className="status-card__label">Dry-run manual review</p><p className="status-card__value">{summary?.dry_run_manual_review ?? 0}</p></article>
        </section>

        <SectionCard eyebrow="Order intents" title="Broker-like intents" description="Intent translation log between paper execution and future real-execution adapters.">
          {intents.length === 0 ? (
            <EmptyState title="No broker intents yet." description="Create a dry-run broker intent from an execution-ready source." />
          ) : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Source</th><th>Market</th><th>Side</th><th>Qty</th><th>Status</th><th>Validation</th><th>Blocking reasons</th><th>Created at</th></tr></thead>
                <tbody>
                  {intents.map((intent) => {
                    const latestValidation = intent.validations?.[0];
                    return (
                      <tr key={intent.id} onClick={() => setSelectedIntentId(intent.id)}>
                        <td>{intent.source_ref}</td>
                        <td>{intent.market_title ?? intent.market_ref ?? '—'}</td>
                        <td>{intent.side}</td>
                        <td>{intent.quantity}</td>
                        <td><StatusBadge tone={STATUS_TONE[intent.status] ?? 'neutral'}>{intent.status}</StatusBadge></td>
                        <td>{latestValidation ? <StatusBadge tone={latestValidation.is_valid ? 'ready' : 'offline'}>{latestValidation.outcome}</StatusBadge> : '—'}</td>
                        <td>{latestValidation?.blocking_reasons?.join('; ') || '—'}</td>
                        <td>{intent.created_at}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Intent detail" title={selectedIntent ? `Intent #${selectedIntent.id}` : 'Select an intent'} description="Mapping, envelope checks, runtime/safety/certification checks and simulated broker response.">
          {!selectedIntent ? (
            <p>Select an intent to inspect mapping details and dry-run response.</p>
          ) : (
            <div className="stack-sm">
              <p><strong>Mapping profile:</strong> {selectedIntent.mapping_profile}</p>
              <p><strong>Symbol / market ref:</strong> {selectedIntent.symbol || '—'} / {selectedIntent.market_ref || '—'}</p>
              <p><strong>Order type:</strong> {selectedIntent.order_type} · <strong>TIF:</strong> {selectedIntent.time_in_force}</p>
              <p><strong>Validation checks:</strong> {selectedIntent.validations?.[0] ? JSON.stringify(selectedIntent.validations[0].checks) : 'Not validated yet'}</p>
              <p><strong>Warnings:</strong> {selectedIntent.validations?.[0]?.warnings?.join('; ') || '—'}</p>
              <p><strong>Missing fields:</strong> {selectedIntent.validations?.[0]?.missing_fields?.join(', ') || '—'}</p>
              <p><strong>Dry-run response:</strong> {selectedIntent.dry_runs?.[0] ? <StatusBadge tone={STATUS_TONE[selectedIntent.dry_runs[0].simulated_response] ?? 'neutral'}>{selectedIntent.dry_runs[0].simulated_response}</StatusBadge> : 'Not executed'}</p>
              {selectedIntent.dry_runs?.[0]?.dry_run_summary ? <p><strong>Dry-run summary:</strong> {selectedIntent.dry_runs[0].dry_run_summary}</p> : null}
            </div>
          )}
        </SectionCard>
      </DataStateWrapper>
    </div>
  );
}

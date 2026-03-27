import { useCallback, useEffect, useMemo, useState } from 'react';

import { EmptyState } from '../components/EmptyState';
import { PageHeader } from '../components/PageHeader';
import { SectionCard } from '../components/SectionCard';
import { StatusBadge } from '../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../components/markets/DataStateWrapper';
import { getBrokerIntents } from '../services/brokerBridge';
import { buildVenuePayload, dryRunVenueIntent, getVenueCapabilities, getVenueParityRuns, getVenueSummary, runVenueParity } from '../services/executionVenue';
import type { BrokerOrderIntent } from '../types/brokerBridge';
import type { VenueOrderPayload, VenueOrderResponse, VenueParityRun, VenueSummary } from '../types/executionVenue';

const STATUS_TONE: Record<string, 'ready' | 'pending' | 'offline' | 'neutral'> = {
  ACCEPTED: 'ready',
  REJECTED: 'offline',
  HOLD: 'pending',
  REQUIRES_CONFIRMATION: 'pending',
  UNSUPPORTED: 'offline',
  INVALID_PAYLOAD: 'offline',
  PARITY_OK: 'ready',
  PARITY_GAP: 'pending',
};

export function ExecutionVenuePage() {
  const [intents, setIntents] = useState<BrokerOrderIntent[]>([]);
  const [capability, setCapability] = useState<any | null>(null);
  const [summary, setSummary] = useState<VenueSummary | null>(null);
  const [parityRuns, setParityRuns] = useState<VenueParityRun[]>([]);
  const [selectedIntentId, setSelectedIntentId] = useState<number | null>(null);
  const [payloadPreview, setPayloadPreview] = useState<VenueOrderPayload | null>(null);
  const [responsePreview, setResponsePreview] = useState<VenueOrderResponse | null>(null);
  const [validationPreview, setValidationPreview] = useState<{ is_valid: boolean; reason_codes: string[]; warnings: string[]; missing_fields: string[] } | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [intentData, capabilityData, summaryData, parityData] = await Promise.all([
        getBrokerIntents(),
        getVenueCapabilities(),
        getVenueSummary(),
        getVenueParityRuns(),
      ]);
      setIntents(intentData);
      setCapability(capabilityData);
      setSummary(summaryData);
      setParityRuns(parityData);
      setSelectedIntentId((prev) => prev ?? intentData[0]?.id ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load execution venue state.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const selectedIntent = useMemo(() => intents.find((intent) => intent.id === selectedIntentId) ?? null, [intents, selectedIntentId]);

  async function handleBuildPayload() {
    if (!selectedIntent) return;
    setBusy(true);
    setError(null);
    try {
      const result = await buildVenuePayload(selectedIntent.id, { metadata: { triggered_from: 'execution_venue_page' } });
      setPayloadPreview(result.payload);
      setValidationPreview(result.validation);
      setResponsePreview(null);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not build venue payload.');
    } finally {
      setBusy(false);
    }
  }

  async function handleDryRun() {
    if (!selectedIntent) return;
    setBusy(true);
    setError(null);
    try {
      const result = await dryRunVenueIntent(selectedIntent.id, { metadata: { triggered_from: 'execution_venue_page' } });
      setPayloadPreview(result.payload);
      setResponsePreview(result.response);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not run venue sandbox dry-run.');
    } finally {
      setBusy(false);
    }
  }

  async function handleRunParity() {
    if (!selectedIntent) return;
    setBusy(true);
    setError(null);
    try {
      const result = await runVenueParity(selectedIntent.id, { metadata: { triggered_from: 'execution_venue_page' } });
      setPayloadPreview(result.payload);
      setResponsePreview(result.response);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not run venue parity harness.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Execution venue contract"
        title="Execution Venue"
        description="Canonical external execution contract and sandbox adapter harness for future broker/exchange integration. Sandbox only: no credentials, no live routes, no real orders."
      />

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard
          eyebrow="Sandbox boundary"
          title="Live remains disabled by design"
          description="This layer only builds canonical payloads, simulates venue responses, and runs parity checks across broker bridge and execution simulator evidence."
        >
          <p>
            <StatusBadge tone="pending">SANDBOX_ONLY</StatusBadge> · <strong>Adapter:</strong> {capability?.adapter_name ?? 'null_sandbox'} ·{' '}
            <strong>Live supported:</strong> {String(capability?.live_supported ?? false)}
          </p>
          <p>
            Need policy and approvals? Continue using <a href="/go-live">Go-Live Gate</a>. Need intent creation? Use <a href="/broker-bridge">Broker Bridge</a> first.
          </p>
        </SectionCard>

        <section className="stats-grid">
          <article className="status-card"><p className="status-card__label">Total parity runs</p><p className="status-card__value">{summary?.total_runs ?? 0}</p></article>
          <article className="status-card"><p className="status-card__label">PARITY_OK</p><p className="status-card__value">{summary?.parity_ok ?? 0}</p></article>
          <article className="status-card"><p className="status-card__label">PARITY_GAP</p><p className="status-card__value">{summary?.parity_gap ?? 0}</p></article>
          <article className="status-card"><p className="status-card__label">Avg readiness</p><p className="status-card__value">{summary?.avg_readiness_score ?? 0}</p></article>
        </section>

        <SectionCard eyebrow="Capabilities" title="Adapter capability profile" description="Stable, auditable venue capability contract. Useful for compatibility checks before any real integration.">
          {!capability ? (
            <p>No capability profile found.</p>
          ) : (
            <div className="stack-sm">
              <p><strong>Venue:</strong> {capability.venue_name}</p>
              <p><strong>Supports:</strong> market={String(capability.supports_market_like)} · limit={String(capability.supports_limit_like)} · reduce_only={String(capability.supports_reduce_only)} · close={String(capability.supports_close_order)}</p>
              <p><strong>Constraints:</strong> requires_symbol_mapping={String(capability.requires_symbol_mapping)} · manual_confirmation={String(capability.requires_manual_confirmation)} · paper_only_supported={String(capability.paper_only_supported)}</p>
            </div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Payload + parity" title="Build payload and run parity" description="Select a broker intent, build canonical venue payload, run sandbox dry-run, and execute parity harness.">
          {intents.length === 0 ? (
            <EmptyState title="No broker intents available." description="Create a broker intent first to test venue parity." />
          ) : (
            <div className="button-row">
              <select value={selectedIntentId ?? ''} onChange={(event) => setSelectedIntentId(Number(event.target.value))}>
                {intents.map((intent) => (
                  <option key={intent.id} value={intent.id}>Intent #{intent.id} · {intent.market_title ?? intent.market_ref ?? 'unknown'} · {intent.status}</option>
                ))}
              </select>
              <button type="button" className="secondary-button" disabled={busy || !selectedIntent} onClick={() => void handleBuildPayload()}>Build payload</button>
              <button type="button" className="secondary-button" disabled={busy || !selectedIntent} onClick={() => void handleDryRun()}>Run sandbox dry-run</button>
              <button type="button" className="primary-button" disabled={busy || !selectedIntent} onClick={() => void handleRunParity()}>Run parity</button>
            </div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Canonical contract" title="Payload and normalized response" description="Stable order contract and normalized venue simulation response.">
          <div className="stack-sm">
            <p><strong>Payload:</strong> {payloadPreview ? JSON.stringify(payloadPreview) : 'Build payload to inspect canonical contract.'}</p>
            <p>
              <strong>Validation:</strong>{' '}
              {validationPreview ? (
                <>
                  <StatusBadge tone={validationPreview.is_valid ? 'ready' : 'pending'}>{validationPreview.is_valid ? 'VALID' : 'INVALID'}</StatusBadge> · missing={validationPreview.missing_fields.join(', ') || 'none'} · reason_codes={validationPreview.reason_codes.join(', ') || 'none'}
                </>
              ) : (
                'Run build payload for validation details.'
              )}
            </p>
            <p>
              <strong>Response:</strong>{' '}
              {responsePreview ? <StatusBadge tone={STATUS_TONE[responsePreview.normalized_status] ?? 'neutral'}>{responsePreview.normalized_status}</StatusBadge> : 'Run sandbox dry-run to inspect response.'}
            </p>
            {responsePreview ? <p><strong>Warnings:</strong> {responsePreview.warnings.join(', ') || 'none'} · <strong>Reason codes:</strong> {responsePreview.reason_codes.join(', ') || 'none'}</p> : null}
          </div>
        </SectionCard>

        <SectionCard eyebrow="Parity history" title="Venue parity runs" description="Auditable parity runs between broker dry-run, execution simulator context, and canonical sandbox adapter contract.">
          {parityRuns.length === 0 ? (
            <EmptyState title="No parity runs yet." description="Run a parity check from the panel above." />
          ) : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Intent</th><th>Status</th><th>Parity</th><th>Issues</th><th>Readiness</th><th>Created</th></tr></thead>
                <tbody>
                  {parityRuns.map((run) => (
                    <tr key={run.id}>
                      <td>#{run.intent}</td>
                      <td>{run.response ? <StatusBadge tone={STATUS_TONE[run.response.normalized_status] ?? 'neutral'}>{run.response.normalized_status}</StatusBadge> : '—'}</td>
                      <td><StatusBadge tone={STATUS_TONE[run.parity_status] ?? 'neutral'}>{run.parity_status}</StatusBadge></td>
                      <td>{[...run.issues, ...run.missing_fields, ...run.unsupported_actions].join(' · ') || 'none'}</td>
                      <td>{run.readiness_score}</td>
                      <td>{run.created_at}</td>
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

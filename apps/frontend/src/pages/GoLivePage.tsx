import { useCallback, useEffect, useMemo, useState } from 'react';

import { EmptyState } from '../components/EmptyState';
import { PageHeader } from '../components/PageHeader';
import { SectionCard } from '../components/SectionCard';
import { StatusBadge } from '../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../components/markets/DataStateWrapper';
import { getBrokerIntents } from '../services/brokerBridge';
import {
  createGoLiveApprovalRequest,
  getGoLiveApprovals,
  getGoLiveChecklists,
  getGoLiveRehearsals,
  getGoLiveState,
  getGoLiveSummary,
  runGoLiveChecklist,
  runGoLiveRehearsal,
} from '../services/goLive';
import type { BrokerOrderIntent } from '../types/brokerBridge';
import type { GoLiveApprovalRequest, GoLiveChecklistRun, GoLiveRehearsalRun, GoLiveState, GoLiveSummary } from '../types/goLive';

const TONE_BY_STATE: Record<string, 'ready' | 'pending' | 'offline' | 'neutral'> = {
  PAPER_ONLY_LOCKED: 'neutral',
  PRELIVE_REHEARSAL_READY: 'ready',
  MANUAL_APPROVAL_PENDING: 'pending',
  LIVE_DISABLED_BY_POLICY: 'offline',
  REMEDIATION_REQUIRED: 'offline',
};

export function GoLivePage() {
  const [state, setState] = useState<GoLiveState | null>(null);
  const [summary, setSummary] = useState<GoLiveSummary | null>(null);
  const [checklists, setChecklists] = useState<GoLiveChecklistRun[]>([]);
  const [approvals, setApprovals] = useState<GoLiveApprovalRequest[]>([]);
  const [rehearsals, setRehearsals] = useState<GoLiveRehearsalRun[]>([]);
  const [intents, setIntents] = useState<BrokerOrderIntent[]>([]);
  const [selectedIntentId, setSelectedIntentId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [stateData, summaryData, checklistData, approvalData, rehearsalData, intentsData] = await Promise.all([
        getGoLiveState(),
        getGoLiveSummary(),
        getGoLiveChecklists(),
        getGoLiveApprovals(),
        getGoLiveRehearsals(),
        getBrokerIntents(),
      ]);
      setState(stateData);
      setSummary(summaryData);
      setChecklists(checklistData);
      setApprovals(approvalData);
      setRehearsals(rehearsalData);
      setIntents(intentsData);
      setSelectedIntentId((prev) => prev ?? intentsData[0]?.id ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load go-live gate data.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const selectedIntent = useMemo(() => intents.find((intent) => intent.id === selectedIntentId) ?? null, [intents, selectedIntentId]);

  async function handleRunChecklist() {
    setBusy(true);
    setError(null);
    try {
      await runGoLiveChecklist({ requested_by: 'local-operator', context: 'ui', manual_inputs: { operator_review_complete: true } });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not run checklist.');
    } finally {
      setBusy(false);
    }
  }

  async function handleCreateApprovalRequest() {
    setBusy(true);
    setError(null);
    try {
      await createGoLiveApprovalRequest({
        requested_by: 'local-operator',
        rationale: 'Manual pre-live review requested from go-live page.',
        scope: 'global',
        requested_mode: 'PRELIVE_REHEARSAL',
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create approval request.');
    } finally {
      setBusy(false);
    }
  }

  async function handleRunRehearsal() {
    if (!selectedIntent) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await runGoLiveRehearsal({ intent_id: selectedIntent.id, requested_by: 'local-operator' });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not run rehearsal.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Final gate (paper-only)"
        title="Go-Live Rehearsal Gate"
        description="Formal pre-live rehearsal layer with checklist, manual approvals, and an explicit capital firewall. This page never submits real orders."
      />

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard
          eyebrow="Capital firewall"
          title="Live execution remains blocked"
          description="Expected and healthy behavior: live routing is disabled by policy and all actions stay in rehearsal/dry-run mode."
        >
          <p>
            <strong>Firewall status:</strong>{' '}
            <StatusBadge tone={state?.firewall?.blocked_by_firewall ? 'offline' : 'ready'}>
              {state?.firewall?.blocked_by_firewall ? 'BLOCKED_BY_FIREWALL' : 'NOT_BLOCKED'}
            </StatusBadge>
          </p>
          <p>
            <strong>Current gate:</strong>{' '}
            <StatusBadge tone={TONE_BY_STATE[state?.state ?? 'PAPER_ONLY_LOCKED'] ?? 'neutral'}>{state?.state ?? 'PAPER_ONLY_LOCKED'}</StatusBadge>
          </p>
          <p><strong>Policy blockers:</strong> {(state?.blockers ?? []).join(' · ') || 'None listed'}</p>
          <p>
            For canonical venue payload mapping and parity diagnostics, use <a href="/execution-venue">Execution Venue</a>.
          </p>
          <p>
            For sandbox external account/order/position reconciliation parity, use <a href="/venue-account">Venue Account Mirror</a>.
          </p>
        </SectionCard>

        <section className="stats-grid">
          <article className="status-card"><p className="status-card__label">Checklist runs</p><p className="status-card__value">{summary?.checklists.total ?? 0}</p></article>
          <article className="status-card"><p className="status-card__label">Checklist passed</p><p className="status-card__value">{summary?.checklists.passed ?? 0}</p></article>
          <article className="status-card"><p className="status-card__label">Approvals</p><p className="status-card__value">{summary?.approvals.total ?? 0}</p></article>
          <article className="status-card"><p className="status-card__label">Rehearsals</p><p className="status-card__value">{summary?.rehearsals.total ?? 0}</p></article>
        </section>

        <SectionCard eyebrow="Checklist" title="Pre-live checklist" description="Run and inspect persisted checklist evidence before any final rehearsal.">
          <div className="button-row">
            <button type="button" className="primary-button" onClick={() => void handleRunChecklist()} disabled={busy}>Run checklist</button>
          </div>
          {checklists.length === 0 ? (
            <EmptyState title="No checklist runs yet." description="Run a pre-live checklist before any final rehearsal." />
          ) : (
            <div className="stack-sm">
              <p><strong>Latest passed items:</strong> {checklists[0].passed_items.join(', ') || '—'}</p>
              <p><strong>Latest failed items:</strong> {checklists[0].failed_items.join(', ') || '—'}</p>
              <p><strong>Latest blocking reasons:</strong> {checklists[0].blocking_reasons.join(' · ') || '—'}</p>
            </div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Manual approvals" title="Approval requests" description="Manual-first approvals are required and never auto-applied.">
          <div className="button-row">
            <button type="button" className="secondary-button" onClick={() => void handleCreateApprovalRequest()} disabled={busy}>Request approval</button>
          </div>
          {approvals.length === 0 ? (
            <EmptyState title="No approvals yet." description="Create a manual approval request before final rehearsal decisions." />
          ) : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>ID</th><th>Requested by</th><th>Status</th><th>Scope</th><th>Mode</th><th>Created</th></tr></thead>
                <tbody>
                  {approvals.map((approval) => (
                    <tr key={approval.id}>
                      <td>{approval.id}</td>
                      <td>{approval.requested_by}</td>
                      <td><StatusBadge tone={approval.status === 'APPROVED' ? 'ready' : approval.status === 'REJECTED' ? 'offline' : 'pending'}>{approval.status}</StatusBadge></td>
                      <td>{approval.scope}</td>
                      <td>{approval.requested_mode}</td>
                      <td>{approval.created_at}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Final rehearsal" title="Last-meter dry-run rehearsal" description="Run the final gate rehearsal on a broker intent. It executes dry-run only and records missing preconditions/approvals/firewall blockers.">
          <div className="button-row">
            <select value={selectedIntentId ?? ''} onChange={(event) => setSelectedIntentId(Number(event.target.value))}>
              {intents.map((intent) => (
                <option value={intent.id} key={intent.id}>Intent #{intent.id} · {intent.market_title ?? intent.market_ref ?? 'unknown'} · {intent.status}</option>
              ))}
            </select>
            <button type="button" className="primary-button" onClick={() => void handleRunRehearsal()} disabled={busy || !selectedIntent}>Run final rehearsal</button>
          </div>

          {rehearsals.length === 0 ? (
            <EmptyState title="No rehearsals yet." description="Run a pre-live checklist before any final rehearsal." />
          ) : (
            <div className="stack-sm">
              <p><strong>Latest rehearsal result:</strong> <StatusBadge tone={rehearsals[0].allowed_to_proceed_in_rehearsal ? 'ready' : 'offline'}>{rehearsals[0].allowed_to_proceed_in_rehearsal ? 'ALLOWED_IN_REHEARSAL' : 'BLOCKED'}</StatusBadge></p>
              <p><strong>Dry-run disposition:</strong> {rehearsals[0].final_dry_run_disposition || '—'}</p>
              <p><strong>Blocked by firewall:</strong> {rehearsals[0].blocked_by_firewall ? 'Yes (expected)' : 'No'}</p>
              <p><strong>Missing approvals:</strong> {rehearsals[0].missing_approvals.join(', ') || '—'}</p>
              <p><strong>Missing preconditions:</strong> {rehearsals[0].missing_preconditions.join(', ') || '—'}</p>
              <p><strong>Blocked reasons:</strong> {rehearsals[0].blocked_reasons.join(' · ') || '—'}</p>
            </div>
          )}
        </SectionCard>
      </DataStateWrapper>
    </div>
  );
}

import { useCallback, useEffect, useMemo, useState } from 'react';

import { EmptyState } from '../../components/EmptyState';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { navigate } from '../../lib/router';
import { approveRequest, escalateRequest, expireRequest, getApprovals, getApprovalSummary, rejectRequest } from '../../services/approvals';
import type { ApprovalRequest } from '../../types/approvals';

const formatDate = (value: string | null | undefined) => (value ? new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) : '—');

const toneByStatus = (status: string): 'ready' | 'pending' | 'offline' | 'neutral' => {
  if (status === 'APPROVED') return 'ready';
  if (status === 'PENDING') return 'pending';
  if (['REJECTED', 'EXPIRED', 'ESCALATED'].includes(status)) return 'offline';
  return 'neutral';
};

const sourceLabel = (source: ApprovalRequest['source_type']) => source.split('_').join(' ');

export function ApprovalCenterPage() {
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);
  const [summary, setSummary] = useState<{ pending: number; high_priority_pending: number; approved_recently: number; expired_or_escalated: number } | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [queue, queueSummary] = await Promise.all([getApprovals(), getApprovalSummary()]);
      setApprovals(queue);
      setSummary(queueSummary);
      if (!selectedId && queue.length > 0) {
        setSelectedId(queue[0].id);
      }
      if (selectedId && !queue.find((item) => item.id === selectedId)) {
        setSelectedId(queue[0]?.id ?? null);
      }
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Could not load approvals.');
      setApprovals([]);
    } finally {
      setLoading(false);
    }
  }, [selectedId]);

  useEffect(() => { void load(); }, [load]);

  const selected = useMemo(() => approvals.find((item) => item.id === selectedId) ?? null, [approvals, selectedId]);

  const runDecision = useCallback(async (kind: 'approve' | 'reject' | 'expire' | 'escalate') => {
    if (!selected) return;
    setActionLoading(true);
    setError(null);
    setMessage(null);
    try {
      if (kind === 'approve') await approveRequest(selected.id, { rationale: 'Approved from unified approval center.' });
      if (kind === 'reject') await rejectRequest(selected.id, { rationale: 'Rejected from unified approval center.' });
      if (kind === 'expire') await expireRequest(selected.id, { rationale: 'Expired from unified approval center.' });
      if (kind === 'escalate') await escalateRequest(selected.id, { rationale: 'Escalated from unified approval center.' });
      setMessage(`Decision ${kind.toUpperCase()} recorded for request #${selected.id}.`);
      await load();
    } catch (decisionError) {
      setError(decisionError instanceof Error ? decisionError.message : `Decision ${kind} failed.`);
    } finally {
      setActionLoading(false);
    }
  }, [load, selected]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Human-in-the-loop control plane"
        title="/approvals"
        description="Unified approval center for manual-first decision gates across runbooks, go-live, and approval-required operator queue items. Every decision is explicit, traceable, and paper/sandbox only."
        actions={<div className="button-row"><button type="button" className="secondary-button" onClick={() => navigate('/cockpit')}>Open cockpit</button><button type="button" className="secondary-button" onClick={() => navigate('/trace')}>Open trace</button><button type="button" className="secondary-button" onClick={() => void load()}>Refresh</button></div>}
      />

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Summary" title="Approval queue posture" description="Centralized counts for pending, high-priority, recent approvals, and expired/escalated outcomes.">
          <div className="cockpit-metric-grid">
            <div><strong>Pending</strong><div>{summary?.pending ?? 0}</div></div>
            <div><strong>High priority pending</strong><div>{summary?.high_priority_pending ?? 0}</div></div>
            <div><strong>Approved (24h)</strong><div>{summary?.approved_recently ?? 0}</div></div>
            <div><strong>Expired / escalated</strong><div>{summary?.expired_or_escalated ?? 0}</div></div>
          </div>
        </SectionCard>

        <SectionCard eyebrow="Approval queue" title="Unified decision gates" description="Centralized pending/resolved approval requests with source, impact preview, and trace links.">
          {approvals.length === 0 ? (
            <EmptyState eyebrow="Approvals" title="No pending approvals right now." description="No centralized approval requests are currently pending. Resolved approvals remain available as healthy history." />
          ) : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Source</th><th>Title</th><th>Priority</th><th>Status</th><th>Requested</th><th>Impact preview</th><th>Trace</th></tr></thead>
                <tbody>
                  {approvals.map((approval) => (
                    <tr key={approval.id}>
                      <td><button type="button" className="link-button" onClick={() => setSelectedId(approval.id)}>{sourceLabel(approval.source_type)}</button></td>
                      <td>{approval.title}</td>
                      <td><StatusBadge tone={approval.priority === 'HIGH' || approval.priority === 'CRITICAL' ? 'pending' : 'neutral'}>{approval.priority}</StatusBadge></td>
                      <td><StatusBadge tone={toneByStatus(approval.status)}>{approval.status}</StatusBadge></td>
                      <td>{formatDate(approval.requested_at)}</td>
                      <td>{approval.impact_preview?.approve ?? approval.metadata?.impact_preview?.approve ?? '—'}</td>
                      <td>{approval.metadata?.trace ? <button type="button" className="link-button" onClick={() => { const trace = approval.metadata?.trace; if (!trace) return; navigate(`/trace?root_type=${encodeURIComponent(trace.root_type)}&root_id=${encodeURIComponent(trace.root_id)}`); }}>Open trace</button> : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Detail" title={selected ? `Approval #${selected.id}` : 'Select approval request'} description="Context, impact, evidence, and explicit decision controls.">
          {!selected ? <EmptyState eyebrow="Detail" title="Select an approval" description="Choose a row to inspect impact preview and decide." /> : (
            <div className="page-stack">
              <p><strong>Source:</strong> {sourceLabel(selected.source_type)} · <strong>Source object:</strong> {selected.source_object_id}</p>
              <p><strong>Status:</strong> <StatusBadge tone={toneByStatus(selected.status)}>{selected.status}</StatusBadge> · <strong>Priority:</strong> <StatusBadge tone={selected.priority === 'HIGH' || selected.priority === 'CRITICAL' ? 'pending' : 'neutral'}>{selected.priority}</StatusBadge></p>
              <p><strong>Summary:</strong> {selected.summary || '—'}</p>
              <p><strong>Requested at:</strong> {formatDate(selected.requested_at)} · <strong>Expires at:</strong> {formatDate(selected.expires_at)}</p>

              <SectionCard eyebrow="Impact preview" title="Decision outcomes" description="Audit-friendly preview of what each action changes.">
                <ul>
                  <li><strong>Approve:</strong> {selected.impact_preview.approve}</li>
                  <li><strong>Reject:</strong> {selected.impact_preview.reject}</li>
                  <li><strong>Expire:</strong> {selected.impact_preview.expire}</li>
                  <li><strong>Escalate:</strong> {selected.impact_preview.escalate}</li>
                </ul>
                <p><strong>Evidence to review:</strong> {(selected.impact_preview.evidence || []).join(' · ') || 'n/a'}</p>
              </SectionCard>

              <div className="button-row">
                <button type="button" className="primary-button" disabled={actionLoading || selected.status !== 'PENDING'} onClick={() => void runDecision('approve')}>Approve</button>
                <button type="button" className="secondary-button" disabled={actionLoading || selected.status !== 'PENDING'} onClick={() => void runDecision('reject')}>Reject</button>
                <button type="button" className="ghost-button" disabled={actionLoading || selected.status !== 'PENDING'} onClick={() => void runDecision('expire')}>Expire</button>
                <button type="button" className="ghost-button" disabled={actionLoading} onClick={() => void runDecision('escalate')}>Escalate</button>
                {selected.metadata?.trace ? <button type="button" className="secondary-button" onClick={() => { const trace = selected.metadata?.trace; if (!trace) return; navigate(`/trace?root_type=${encodeURIComponent(trace.root_type)}&root_id=${encodeURIComponent(trace.root_id)}`); }}>Open related trace</button> : null}
              </div>

              {selected.decisions.length > 0 ? (
                <div className="table-wrapper">
                  <table className="data-table">
                    <thead><tr><th>Decision</th><th>By</th><th>Rationale</th><th>At</th></tr></thead>
                    <tbody>
                      {selected.decisions.map((decision) => (
                        <tr key={decision.id}><td>{decision.decision}</td><td>{decision.decided_by}</td><td>{decision.rationale || '—'}</td><td>{formatDate(decision.created_at)}</td></tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : <p className="muted-text">No manual decision logs yet.</p>}
            </div>
          )}
        </SectionCard>
      </DataStateWrapper>
      {message ? <p className="success-text">{message}</p> : null}
    </div>
  );
}

import { useCallback, useEffect, useMemo, useState } from 'react';
import { EmptyState } from '../../components/EmptyState';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import {
  approveOperatorQueueItem,
  getOperatorQueueItems,
  getOperatorQueueSummary,
  rejectOperatorQueueItem,
  snoozeOperatorQueueItem,
} from '../../services/operatorQueue';
import type { OperatorQueueItem, OperatorQueuePriority, OperatorQueueSummary } from '../../types/operatorQueue';

function toneFromStatus(status: string) {
  if (status === 'EXECUTED' || status === 'APPROVED') return 'ready';
  if (status === 'PENDING' || status === 'SNOOZED') return 'pending';
  if (status === 'REJECTED' || status === 'EXPIRED') return 'offline';
  return 'neutral';
}

function toneFromPriority(priority: OperatorQueuePriority) {
  if (priority === 'critical') return 'offline';
  if (priority === 'high') return 'pending';
  return 'neutral';
}

function formatDate(value: string | null) {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short' }).format(date);
}

export function OperatorQueuePage() {
  const [items, setItems] = useState<OperatorQueueItem[]>([]);
  const [summary, setSummary] = useState<OperatorQueueSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isActionLoading, setIsActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [itemsResponse, summaryResponse] = await Promise.all([getOperatorQueueItems(), getOperatorQueueSummary()]);
      setItems(itemsResponse);
      setSummary(summaryResponse);
      if (!selectedId && itemsResponse.length > 0) {
        setSelectedId(itemsResponse[0].id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load operator queue.');
    } finally {
      setIsLoading(false);
    }
  }, [selectedId]);

  useEffect(() => {
    void load();
  }, [load]);

  const selected = useMemo(() => items.find((item) => item.id === selectedId) ?? null, [items, selectedId]);

  async function runDecision(id: number, decision: 'approve' | 'reject' | 'snooze') {
    setIsActionLoading(true);
    try {
      if (decision === 'approve') {
        await approveOperatorQueueItem(id, 'Approved from operator queue center.');
      } else if (decision === 'reject') {
        await rejectOperatorQueueItem(id, 'Rejected from operator queue center.');
      } else {
        await snoozeOperatorQueueItem(id, { decision_note: 'Snoozed by operator.', snooze_hours: 6 });
      }
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : `Could not ${decision} queue item.`);
    } finally {
      setIsActionLoading(false);
    }
  }

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Operator escalation center"
        title="Operator Queue"
        description="Exception inbox for manual intervention only. The rest of the system keeps running autonomously in paper/demo mode."
      />

      <DataStateWrapper isLoading={isLoading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <div className="dashboard-stats-grid">
          <article className="stat-card"><p className="section-label">Pending</p><h3>{summary?.pending_count ?? 0}</h3></article>
          <article className="stat-card"><p className="section-label">High/Critical</p><h3>{summary?.high_priority_count ?? 0}</h3></article>
          <article className="stat-card"><p className="section-label">Approved recent</p><h3>{summary?.approvals_recent ?? 0}</h3></article>
          <article className="stat-card"><p className="section-label">Rejected recent</p><h3>{summary?.rejected_recent ?? 0}</h3></article>
          <article className="stat-card"><p className="section-label">Snoozed</p><h3>{summary?.snoozed_count ?? 0}</h3></article>
        </div>

        <SectionCard eyebrow="Exception inbox" title="Queue items" description="Centralized approvals/escalations from policy, safety, allocation, semi-auto, continuous-demo, and real-ops contexts.">
          {items.length === 0 ? (
            <EmptyState title="No operator intervention required right now." description="The autonomous paper/demo workflow is currently clear of manual exceptions." eyebrow="Queue clear" />
          ) : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Priority</th><th>Source</th><th>Type</th><th>Market</th><th>Headline</th><th>Action</th><th>Qty</th><th>Created</th><th>Status</th></tr></thead>
                <tbody>
                  {items.map((item) => (
                    <tr key={item.id} onClick={() => setSelectedId(item.id)} style={{ cursor: 'pointer' }}>
                      <td><StatusBadge tone={toneFromPriority(item.priority)}>{item.priority.toUpperCase()}</StatusBadge></td>
                      <td>{item.source}</td>
                      <td>{item.queue_type}</td>
                      <td>{item.market_title || '—'}</td>
                      <td>{item.headline}</td>
                      <td>{item.suggested_action || 'REVIEW'}</td>
                      <td>{item.suggested_quantity ?? '—'}</td>
                      <td>{formatDate(item.created_at)}</td>
                      <td><StatusBadge tone={toneFromStatus(item.status)}>{item.status}</StatusBadge></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Selected detail" title={selected ? `Queue item #${selected.id}` : 'Pick an item'} description="Rationale and execution context for auditable operator decisions.">
          {!selected ? (
            <EmptyState title="Select a queue item" description="Choose one row to review rationale, context, and available manual actions." eyebrow="Detail" />
          ) : (
            <div className="page-stack">
              <p><strong>Why this needs review:</strong> {typeof selected.metadata?.operator_review_reason === 'string' ? selected.metadata.operator_review_reason : selected.summary}</p>
              <p><strong>Rationale:</strong> {selected.rationale || 'No additional rationale provided.'}</p>
              <p><strong>Source/provider context:</strong> {selected.source} · {selected.market_source_type || 'unknown source type'} · {selected.is_real_data ? 'real read-only data' : 'demo data'}</p>
              <p><strong>Execution mode:</strong> paper/demo only (real execution disabled).</p>
              <p><strong>Related IDs:</strong> proposal={selected.related_proposal ?? '—'} pending_approval={selected.related_pending_approval ?? '—'} trade={selected.related_trade ?? '—'}</p>
              <div className="button-row">
                <button type="button" className="primary-button" disabled={isActionLoading} onClick={() => void runDecision(selected.id, 'approve')}>Approve and execute</button>
                <button type="button" className="ghost-button" disabled={isActionLoading} onClick={() => void runDecision(selected.id, 'reject')}>Reject</button>
                <button type="button" className="secondary-button" disabled={isActionLoading} onClick={() => void runDecision(selected.id, 'snooze')}>Snooze</button>
              </div>
            </div>
          )}
        </SectionCard>
      </DataStateWrapper>
    </div>
  );
}

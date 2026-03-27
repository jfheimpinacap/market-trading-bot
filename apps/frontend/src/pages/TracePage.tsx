import { useCallback, useEffect, useMemo, useState } from 'react';

import { EmptyState } from '../components/EmptyState';
import { PageHeader } from '../components/PageHeader';
import { SectionCard } from '../components/SectionCard';
import { StatusBadge } from '../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../components/markets/DataStateWrapper';
import { getTraceQueryRuns, getTraceSummary, runTraceQuery } from '../services/trace';
import type { ProvenanceSnapshot, TraceNode, TraceQueryRun, TraceSummary } from '../types/trace';

const ROOT_TYPES = ['market', 'opportunity', 'proposal', 'paper_order', 'venue_order_snapshot', 'incident', 'mission_cycle', 'position'];

function getInitialQueryParams() {
  const params = new URLSearchParams(window.location.search);
  const rootType = params.get('root_type') ?? 'opportunity';
  const rootId = params.get('root_id') ?? '';
  return { rootType, rootId };
}
const fmtDate = (v: string | null) => (v ? new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(v)) : 'n/a');
const tone = (status: string): 'ready' | 'pending' | 'offline' | 'neutral' => (['SUCCESS', 'FILLED', 'PARITY_OK', 'ACTIVE', 'OPEN', 'READY'].includes(status) ? 'ready' : ['PARTIAL', 'DEGRADED', 'WARNING', 'PAUSED', 'BLOCKED'].includes(status) ? 'pending' : ['FAILED', 'REJECTED', 'CRITICAL'].includes(status) ? 'offline' : 'neutral');

export function TracePage() {
  const initialQuery = getInitialQueryParams();
  const [rootType, setRootType] = useState(ROOT_TYPES.includes(initialQuery.rootType) ? initialQuery.rootType : 'opportunity');
  const [rootId, setRootId] = useState(initialQuery.rootId);
  const [snapshot, setSnapshot] = useState<ProvenanceSnapshot | null>(null);
  const [nodes, setNodes] = useState<TraceNode[]>([]);
  const [queryRuns, setQueryRuns] = useState<TraceQueryRun[]>([]);
  const [summary, setSummary] = useState<TraceSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [partial, setPartial] = useState(false);

  const loadMeta = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [runs, aggregate] = await Promise.all([getTraceQueryRuns(), getTraceSummary()]);
      setQueryRuns(runs);
      setSummary(aggregate);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load trace explorer metadata.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadMeta();
  }, [loadMeta]);

  useEffect(() => {
    if (!rootId.trim()) return;
    void executeQuery();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const executeQuery = useCallback(async () => {
    if (!rootId.trim()) {
      setError('Root id is required.');
      return;
    }
    setRunning(true);
    setError(null);
    try {
      const result = await runTraceQuery({ root_type: rootType, root_id: rootId.trim() });
      setSnapshot(result.snapshot);
      setNodes(result.nodes);
      setPartial(result.partial);
      await loadMeta();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Trace query failed.');
    } finally {
      setRunning(false);
    }
  }, [loadMeta, rootId, rootType]);

  const evidence = useMemo(() => snapshot?.latest_related_evidence ?? [], [snapshot]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Trace explorer"
        title="/trace"
        description="Unified trace explorer and decision provenance for local-first paper/sandbox operations. This view is audit-oriented and does not trigger real execution."
      />

      <SectionCard eyebrow="Query panel" title="Trace query" description="Select root type, provide id, and reconstruct an end-to-end lineage across orchestrator, memory, execution, venue, and incidents.">
        <div className="button-row">
          <label className="field-group"><span>Root type</span><select className="select-input" value={rootType} onChange={(e) => setRootType(e.target.value)}>{ROOT_TYPES.map((type) => <option key={type} value={type}>{type}</option>)}</select></label>
          <label className="field-group"><span>Root id</span><input className="text-input" value={rootId} onChange={(e) => setRootId(e.target.value)} placeholder="e.g. 42" /></label>
          <button type="button" className="primary-button" disabled={running} onClick={() => void executeQuery()}>{running ? 'Querying…' : 'Run trace query'}</button>
        </div>
        {partial ? <p className="muted-text">Partial trace available: not all modules produced linked data for this object yet.</p> : null}
      </SectionCard>

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <div className="content-grid content-grid--two-columns">
          <SectionCard eyebrow="Snapshot" title="Provenance snapshot" description="Current status, key stages, blockers/guards, execution outcome, and incident/degraded context.">
            {!snapshot ? <EmptyState eyebrow="Trace" title="No trace loaded" description="Run a query to inspect end-to-end provenance." /> : (
              <div className="system-metadata-grid">
                <div><strong>Current status:</strong> <StatusBadge tone={tone(snapshot.current_status)}>{snapshot.current_status || 'UNKNOWN'}</StatusBadge></div>
                <div><strong>Node count:</strong> {snapshot.node_count}</div>
                <div><strong>Edge count:</strong> {snapshot.edge_count}</div>
                <div><strong>Key stages:</strong> {snapshot.key_stages.join(' → ') || 'None'}</div>
                <div><strong>Execution outcome:</strong> {snapshot.execution_outcome ? `${snapshot.execution_outcome.type} (${snapshot.execution_outcome.status})` : 'No execution outcome yet'}</div>
                <div><strong>Incident/degraded:</strong> {snapshot.incident_or_degraded_context ? `${snapshot.incident_or_degraded_context.type} (${snapshot.incident_or_degraded_context.status})` : 'None linked'}</div>
              </div>
            )}
          </SectionCard>

          <SectionCard eyebrow="Evidence" title="Related evidence" description="Precedents, incidents, profile/certification context, and venue evidence relevant to this trace.">
            {evidence.length === 0 ? <EmptyState eyebrow="Evidence" title="No evidence found" description="No trace data found for this object yet." /> : (
              <ul>
                {evidence.map((item, index) => <li key={`${item.type}-${index}`}><span className="trace-badge">{item.type.toUpperCase()}</span> {item.title} <StatusBadge tone={tone(item.status)}>{item.status || 'n/a'}</StatusBadge></li>)}
              </ul>
            )}
          </SectionCard>
        </div>

        <SectionCard eyebrow="Timeline" title="Trace nodes and relations" description="Ordered trace nodes with stage badges and concise decision summaries.">
          {nodes.length === 0 ? <EmptyState eyebrow="Timeline" title="No trace nodes" description="No trace data found for this object yet." /> : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Time</th><th>Stage</th><th>Node</th><th>Status</th><th>Summary</th></tr></thead>
                <tbody>
                  {nodes.map((node) => (
                    <tr key={node.id}>
                      <td>{fmtDate(node.happened_at)}</td>
                      <td><span className={`trace-badge trace-badge--${node.stage.toLowerCase()}`}>{node.stage || 'NODE'}</span></td>
                      <td><strong>{node.title}</strong><div className="muted-text">{node.node_type} · {node.ref_type}:{node.ref_id}</div></td>
                      <td><StatusBadge tone={tone(node.status)}>{node.status || 'n/a'}</StatusBadge></td>
                      <td>{node.summary || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Audit trail" title="Recent trace query runs" description="Every query is recorded as an auditable run for reproducibility and operator review.">
          {queryRuns.length === 0 ? <EmptyState eyebrow="Trace runs" title="No query runs yet" description="Run a trace query to create auditable query records." /> : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>When</th><th>Root</th><th>Status</th><th>Nodes</th><th>Edges</th><th>Summary</th></tr></thead>
                <tbody>
                  {queryRuns.slice(0, 12).map((run) => (
                    <tr key={run.id}>
                      <td>{fmtDate(run.created_at)}</td>
                      <td>{run.root_type ?? 'n/a'}:{run.root_object_id ?? 'n/a'}</td>
                      <td><StatusBadge tone={tone(run.status)}>{run.status}{run.partial ? ' (partial)' : ''}</StatusBadge></td>
                      <td>{run.node_count}</td>
                      <td>{run.edge_count}</td>
                      <td>{run.summary}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {summary ? <p className="muted-text">Summary: {summary.total_roots} roots, {summary.total_nodes} nodes, {summary.total_edges} edges.</p> : null}
        </SectionCard>
      </DataStateWrapper>
    </div>
  );
}

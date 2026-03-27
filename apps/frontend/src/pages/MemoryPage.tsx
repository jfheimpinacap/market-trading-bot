import { useCallback, useEffect, useMemo, useState } from 'react';
import { EmptyState } from '../components/EmptyState';
import { PageHeader } from '../components/PageHeader';
import { SectionCard } from '../components/SectionCard';
import { StatusBadge } from '../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../components/markets/DataStateWrapper';
import { navigate } from '../lib/router';
import { getAgentPrecedentUses, getMemoryInfluenceSummary, getMemoryRetrievalRuns, getMemorySummary, runMemoryIndex, runMemoryRetrieval } from '../services/memory';
import type { AgentPrecedentUse, MemoryInfluenceSummary, MemoryRetrievalRun, MemoryRunResponse, MemorySummary } from '../types/memory';

const QUERY_TYPES = ['manual', 'research', 'prediction', 'risk', 'postmortem', 'lifecycle'];

function formatDate(value?: string | null) {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short' }).format(date);
}

function similarityTone(score: number): 'ready' | 'pending' | 'neutral' {
  if (score >= 0.84) return 'ready';
  if (score >= 0.72) return 'pending';
  return 'neutral';
}

export function MemoryPage() {
  const [summary, setSummary] = useState<MemorySummary | null>(null);
  const [runs, setRuns] = useState<MemoryRetrievalRun[]>([]);
  const [uses, setUses] = useState<AgentPrecedentUse[]>([]);
  const [influenceSummary, setInfluenceSummary] = useState<MemoryInfluenceSummary | null>(null);
  const [result, setResult] = useState<MemoryRunResponse | null>(null);
  const [queryText, setQueryText] = useState('Recent volatility with sizing pressure and weak follow-through.');
  const [queryType, setQueryType] = useState('manual');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [indexing, setIndexing] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryRes, runsRes, usesRes] = await Promise.all([getMemorySummary(), getMemoryRetrievalRuns(), getAgentPrecedentUses()]);
      setSummary(summaryRes);
      setRuns(runsRes);
      setUses(usesRes);
      if (!result && summaryRes.last_retrieval_run) {
        setResult({ run: summaryRes.last_retrieval_run, summary: {
          retrieval_run_id: summaryRes.last_retrieval_run.id,
          query_text: summaryRes.last_retrieval_run.query_text,
          query_type: summaryRes.last_retrieval_run.query_type,
          matches: summaryRes.last_retrieval_run.result_count,
          average_similarity: null,
          most_similar_cases: [],
          by_document_type: {},
          prior_caution_signals: [],
          prior_failure_modes: [],
          lessons_learned: [],
        } });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load semantic memory data.');
    } finally {
      setLoading(false);
    }
  }, [result]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const onIndex = async () => {
    setIndexing(true);
    setError(null);
    try {
      await runMemoryIndex();
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Memory indexing failed.');
    } finally {
      setIndexing(false);
    }
  };

  const onRetrieve = async () => {
    if (!queryText.trim()) {
      setError('Write a query first.');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const runRes = await runMemoryRetrieval({ query_text: queryText.trim(), query_type: queryType, limit: 8 });
      setResult(runRes);
      const influence = await getMemoryInfluenceSummary(queryText.trim(), queryType);
      setInfluenceSummary(influence);
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Retrieval failed.');
    } finally {
      setBusy(false);
    }
  };

  const cards = useMemo(() => [
    { label: 'Documents indexed', value: summary?.documents_indexed ?? 0 },
    { label: 'Retrieval runs', value: summary?.retrieval_runs ?? 0 },
    { label: 'Collections/types', value: Object.keys(summary?.document_types ?? {}).length },
    { label: 'Last indexing', value: formatDate(summary?.last_indexed_document_at) },
  ], [summary]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Semantic memory"
        title="Memory / Precedents"
        description="Local-first semantic memory and precedent retrieval layer for research/prediction/risk/postmortem support. Paper/demo only. No real-money execution."
        actions={<div style={{ display: 'flex', gap: '0.75rem' }}>
          <button type="button" className="secondary-button" onClick={() => navigate('/learning')}>Open Learning</button>
          <button type="button" className="secondary-button" onClick={() => navigate('/postmortem-board')}>Open Postmortem Board</button>
          <button type="button" className="secondary-button" onClick={() => navigate('/prediction')}>Open Prediction</button>
          <button type="button" className="secondary-button" onClick={() => navigate('/risk-agent')}>Open Risk Agent</button>
          <button type="button" className="primary-button" disabled={indexing} onClick={() => void onIndex()}>{indexing ? 'Indexing...' : 'Run index'}</button>
        </div>}
      />

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Overview" title="Memory summary" description="Indexed document and retrieval coverage snapshot.">
          <div className="system-metadata-grid">
            {cards.map((card) => <div key={card.label}><strong>{card.label}:</strong> {String(card.value)}</div>)}
          </div>
        </SectionCard>

        <SectionCard eyebrow="Retrieve" title="Precedent query" description="Run semantic retrieval for similar historical cases before making a decision.">
          <div className="button-row">
            <label style={{ flex: 1 }}>Query text
              <input value={queryText} onChange={(event) => setQueryText(event.target.value)} placeholder="Describe scenario, edge, risk context, and concern" />
            </label>
            <label>Query type
              <select value={queryType} onChange={(event) => setQueryType(event.target.value)}>
                {QUERY_TYPES.map((item) => <option key={item} value={item}>{item}</option>)}
              </select>
            </label>
            <button type="button" className="secondary-button" onClick={() => void onRetrieve()} disabled={busy}>{busy ? 'Retrieving...' : 'Run retrieval'}</button>
          </div>
          {!summary?.documents_indexed ? <p style={{ marginTop: '0.75rem' }}>Index learning and review documents first.</p> : null}
        </SectionCard>

        <SectionCard eyebrow="Results" title="Retrieved precedents" description="Most similar cases with source and auditable reasons.">
          {!result?.run.precedents.length ? (
            <EmptyState
              eyebrow="No matches"
              title="No precedents matched yet"
              description="No high-quality match is a valid result. Try a broader query or lower similarity threshold."
            />
          ) : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Rank</th><th>Type</th><th>Title</th><th>Similarity</th><th>Reason</th><th>Source</th></tr></thead>
                <tbody>
                  {result.run.precedents.map((item) => (
                    <tr key={item.id}>
                      <td>{item.rank}</td>
                      <td><StatusBadge tone={similarityTone(item.similarity_score)}>{item.memory_document.document_type.toUpperCase()}</StatusBadge></td>
                      <td>{item.memory_document.title}</td>
                      <td>{item.similarity_score.toFixed(4)}</td>
                      <td>{item.short_reason}</td>
                      <td>{item.memory_document.source_app}#{item.memory_document.source_object_id}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Run history" title="Recent retrieval runs" description="Traceability of precedent lookups and result density.">
          {runs.length === 0 ? <EmptyState title="No retrieval runs yet" description="Run a query above to create the first retrieval run." /> : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>ID</th><th>Query type</th><th>Result count</th><th>Query text</th><th>Created</th></tr></thead>
                <tbody>
                  {runs.slice(0, 15).map((run) => (
                    <tr key={run.id}>
                      <td>{run.id}</td>
                      <td>{run.query_type}</td>
                      <td>{run.result_count}</td>
                      <td>{run.query_text}</td>
                      <td>{formatDate(run.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>
        <SectionCard eyebrow="Audit trail" title="Recent precedent uses" description="Agent-level precedent-aware usage with conservative influence modes.">
          {uses.length === 0 ? <EmptyState title="No precedent uses yet" description="Run research/prediction/risk/postmortem flows to capture precedent-aware decision traces." /> : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>ID</th><th>Agent</th><th>Source</th><th>Precedents</th><th>Influence</th><th>Created</th></tr></thead>
                <tbody>
                  {uses.slice(0, 20).map((use) => (
                    <tr key={use.id}>
                      <td>{use.id}</td>
                      <td>{use.agent_name}</td>
                      <td>{use.source_app}#{use.source_object_id}</td>
                      <td>{use.precedent_count}</td>
                      <td><StatusBadge tone={use.influence_mode === 'caution_boost' ? 'pending' : 'neutral'}>{use.influence_mode}</StatusBadge></td>
                      <td>{formatDate(use.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {influenceSummary ? (
            <p style={{ marginTop: '0.75rem' }}>
              Latest influence summary: mode={influenceSummary.influence_mode}, confidence={influenceSummary.precedent_confidence.toFixed(3)}.
            </p>
          ) : null}
        </SectionCard>
      </DataStateWrapper>
    </div>
  );
}

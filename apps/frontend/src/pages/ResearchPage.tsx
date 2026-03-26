import { useCallback, useEffect, useMemo, useState } from 'react';
import { EmptyState } from '../components/EmptyState';
import { PageHeader } from '../components/PageHeader';
import { SectionCard } from '../components/SectionCard';
import { StatusBadge } from '../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../components/markets/DataStateWrapper';
import { navigate } from '../lib/router';
import {
  getResearchCandidates,
  getResearchItems,
  getResearchSources,
  getResearchSummary,
  runResearchAnalysis,
  runResearchFullScan,
  runResearchIngest,
} from '../services/research';
import { getLlmStatus } from '../services/llm';
import type { NarrativeItem, ResearchCandidate, ResearchSource, ResearchSummary } from '../types/research';
import type { LlmStatusResponse } from '../types/llm';

function fmtDate(value?: string | null) {
  if (!value) return '—';
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short' }).format(d);
}

function sentimentTone(sentiment?: string) {
  if (sentiment === 'bullish') return 'ready';
  if (sentiment === 'bearish') return 'offline';
  if (sentiment === 'mixed') return 'pending';
  return 'neutral';
}

function relationTone(relation: string) {
  if (relation === 'divergence') return 'pending';
  if (relation === 'alignment') return 'ready';
  return 'neutral';
}

function sourceBadge(sourceType: string) {
  if (sourceType === 'reddit') return 'pending';
  if (sourceType === 'rss') return 'ready';
  return 'neutral';
}

export function ResearchPage() {
  const [summary, setSummary] = useState<ResearchSummary | null>(null);
  const [sources, setSources] = useState<ResearchSource[]>([]);
  const [items, setItems] = useState<NarrativeItem[]>([]);
  const [candidates, setCandidates] = useState<ResearchCandidate[]>([]);
  const [llmStatus, setLlmStatus] = useState<LlmStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<'ingest' | 'analysis' | 'full_scan' | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryRes, sourcesRes, itemsRes, candidatesRes, llmRes] = await Promise.all([
        getResearchSummary(),
        getResearchSources(),
        getResearchItems(),
        getResearchCandidates(),
        getLlmStatus(),
      ]);
      setSummary(summaryRes);
      setSources(sourcesRes);
      setItems(itemsRes);
      setCandidates(candidatesRes);
      setLlmStatus(llmRes);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load research data.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const runIngest = async () => {
    setActionLoading('ingest');
    try {
      await runResearchIngest({ run_analysis: true });
      await load();
    } finally {
      setActionLoading(null);
    }
  };

  const runFullScan = async () => {
    setActionLoading('full_scan');
    try {
      await runResearchFullScan();
      await load();
    } finally {
      setActionLoading(null);
    }
  };

  const runAnalysisOnly = async () => {
    setActionLoading('analysis');
    try {
      await runResearchAnalysis();
      await load();
    } finally {
      setActionLoading(null);
    }
  };

  const topItems = useMemo(() => items.slice(0, 20), [items]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Narrative scan + research"
        title="Research"
        description="Mixed narrative ingestion (RSS + Reddit), structured local LLM analysis, and read-only market linking for paper/demo research candidates only."
        actions={(
          <div style={{ display: 'flex', gap: '0.75rem' }}>
            <button type="button" className="secondary-button" onClick={() => navigate('/markets')}>Open Markets</button>
            <button type="button" className="secondary-button" onClick={() => navigate('/prediction')}>Open Prediction</button>
            <button type="button" className="secondary-button" onClick={() => navigate('/agents')}>Open Agents</button>
            <button type="button" className="secondary-button" disabled={actionLoading === 'analysis'} onClick={() => void runAnalysisOnly()}>
              {actionLoading === 'analysis' ? 'Running analysis...' : 'Run analysis'}
            </button>
            <button type="button" className="secondary-button" disabled={actionLoading === 'ingest'} onClick={() => void runIngest()}>
              {actionLoading === 'ingest' ? 'Running ingest...' : 'Run ingest'}
            </button>
            <button type="button" className="secondary-button" disabled={actionLoading === 'full_scan'} onClick={() => void runFullScan()}>
              {actionLoading === 'full_scan' ? 'Running full scan...' : 'Run full research scan'}
            </button>
          </div>
        )}
      />

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Status" title="Research scan summary" description="MVP pipeline: source ingest → analysis → market linking → shortlist.">
          <div className="system-metadata-grid">
            <div><strong>Enabled sources:</strong> {summary?.source_count ?? 0}</div>
            <div><strong>Narrative items:</strong> {summary?.item_count ?? 0}</div>
            <div><strong>Analyzed items:</strong> {summary?.analyzed_count ?? 0}</div>
            <div><strong>Candidates:</strong> {summary?.candidate_count ?? 0}</div>
          </div>
          <div className="system-metadata-grid" style={{ marginTop: '0.8rem' }}>
            <div><strong>RSS sources/items:</strong> {summary?.rss_source_count ?? 0} / {summary?.rss_item_count ?? 0}</div>
            <div><strong>Reddit sources/items:</strong> {summary?.reddit_source_count ?? 0} / {summary?.reddit_item_count ?? 0}</div>
            <div><strong>Mixed candidates:</strong> {summary?.mixed_candidate_count ?? 0}</div>
            <div><strong>Deduped (latest):</strong> {summary?.latest_run?.items_deduplicated ?? 0}</div>
          </div>
          <div className="system-metadata-grid" style={{ marginTop: '0.8rem' }}>
            <div><strong>Latest run:</strong> {summary?.latest_run ? `#${summary.latest_run.id} (${summary.latest_run.status})` : 'No run yet'}</div>
            <div><strong>Last run at:</strong> {fmtDate(summary?.latest_run?.finished_at ?? summary?.latest_run?.started_at)}</div>
            <div><strong>LLM status:</strong> {llmStatus?.status ?? 'unknown'}</div>
            <div><strong>LLM note:</strong> {llmStatus?.message ?? 'Unavailable.'}</div>
          </div>
          {llmStatus && !llmStatus.reachable ? (
            <p style={{ marginTop: '0.75rem' }}><strong>Degraded mode:</strong> narrative analysis falls back to lightweight heuristics until local LLM is reachable.</p>
          ) : null}
        </SectionCard>

        <SectionCard eyebrow="Sources" title="Configured narrative sources" description="RSS/news and Reddit social sources. X/Twitter is intentionally out-of-scope in this phase.">
          {sources.length === 0 ? (
            <EmptyState eyebrow="No sources" title="No narrative sources configured" description="Add an RSS or Reddit source and run ingest first." />
          ) : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Name</th><th>Type</th><th>Detail</th><th>Status</th></tr></thead>
                <tbody>
                  {sources.map((source) => (
                    <tr key={source.id}>
                      <td>{source.name}</td>
                      <td><StatusBadge tone={sourceBadge(source.source_type)}>{source.source_type.toUpperCase()}</StatusBadge></td>
                      <td>{source.source_type === 'reddit' ? `r/${String(source.metadata?.subreddit ?? source.category ?? source.slug)}` : source.feed_url}</td>
                      <td><StatusBadge tone={source.is_enabled ? 'ready' : 'neutral'}>{source.is_enabled ? 'enabled' : 'disabled'}</StatusBadge></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Narrative items" title="Recent ingested items" description="Structured summary/sentiment/topic extraction used for market linking.">
          {topItems.length === 0 ? (
            <EmptyState eyebrow="No items" title="No narrative items yet" description="Add an RSS or Reddit source and run ingest first." />
          ) : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Title</th><th>Source</th><th>Type</th><th>Published</th><th>Sentiment</th><th>Confidence</th><th>Linked markets</th></tr></thead>
                <tbody>
                  {topItems.map((item) => (
                    <tr key={item.id}>
                      <td><a href={item.url} target="_blank" rel="noreferrer">{item.title}</a></td>
                      <td>{item.source_type === 'reddit' ? String((item.metadata?.reddit as { subreddit?: string } | undefined)?.subreddit ?? item.source_name) : item.source_name}</td>
                      <td><StatusBadge tone={sourceBadge(item.source_type)}>{item.source_type.toUpperCase()}</StatusBadge></td>
                      <td>{fmtDate(item.published_at)}</td>
                      <td><StatusBadge tone={sentimentTone(item.analysis?.sentiment)}>{item.analysis?.sentiment ?? 'pending'}</StatusBadge></td>
                      <td>{item.analysis?.confidence ?? '—'}</td>
                      <td>{item.linked_market_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Shortlist" title="Research candidates" description="Narrative-vs-market comparison for divergence/alignment triage. Paper/demo only.">
          {candidates.length === 0 ? (
            <EmptyState eyebrow="No candidates" title="No research candidates yet" description="Run ingest/analysis and market linking to populate shortlist." />
          ) : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Market</th><th>Narrative direction</th><th>Source mix</th><th>Relation</th><th>Priority</th><th>Thesis</th><th>Actions</th></tr></thead>
                <tbody>
                  {candidates.map((candidate) => (
                    <tr key={candidate.id}>
                      <td><button type="button" className="link-button" onClick={() => navigate(`/markets/${candidate.market_slug}`)}>{candidate.market_title}</button></td>
                      <td><StatusBadge tone={sentimentTone(candidate.sentiment_direction)}>{candidate.sentiment_direction}</StatusBadge></td>
                      <td><StatusBadge tone={sourceBadge(candidate.source_mix.includes('social') ? 'reddit' : 'rss')}>{candidate.source_mix.toUpperCase()}</StatusBadge></td>
                      <td><StatusBadge tone={relationTone(candidate.relation)}>{candidate.relation}</StatusBadge></td>
                      <td>{candidate.priority}</td>
                      <td>{candidate.short_thesis}</td>
                      <td><button type="button" className="link-button" onClick={() => navigate(`/prediction?market_id=${candidate.market}`)}>Score in prediction agent</button></td>
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

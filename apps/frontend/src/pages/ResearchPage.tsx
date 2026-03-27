import { useCallback, useEffect, useMemo, useState } from 'react';
import { EmptyState } from '../components/EmptyState';
import { PageHeader } from '../components/PageHeader';
import { SectionCard } from '../components/SectionCard';
import { StatusBadge } from '../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../components/markets/DataStateWrapper';
import { navigate } from '../lib/router';
import {
  getPursuitCandidates,
  getResearchBoardSummary,
  getResearchCandidates,
  getResearchItems,
  getResearchSources,
  getResearchSummary,
  runResearchAnalysis,
  runResearchFullScan,
  runResearchIngest,
  runTriageToPrediction,
  runUniverseScan,
} from '../services/research';
import { getLlmStatus } from '../services/llm';
import type {
  NarrativeItem,
  PursuitCandidate,
  ResearchBoardSummary,
  ResearchCandidate,
  ResearchSource,
  ResearchSummary,
} from '../types/research';
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
  if (sourceType === 'twitter') return 'pending';
  if (sourceType === 'rss') return 'ready';
  return 'neutral';
}

function sourceMixBadge(sourceMix: string) {
  if (sourceMix === 'full_signal' || sourceMix === 'news_confirmed') return 'ready';
  if (sourceMix === 'social_heavy' || sourceMix === 'mixed') return 'pending';
  return 'neutral';
}

function triageTone(status: string) {
  if (status === 'shortlisted') return 'ready';
  if (status === 'watch') return 'pending';
  return 'neutral';
}

export function ResearchPage() {
  const [summary, setSummary] = useState<ResearchSummary | null>(null);
  const [boardSummary, setBoardSummary] = useState<ResearchBoardSummary | null>(null);
  const [sources, setSources] = useState<ResearchSource[]>([]);
  const [items, setItems] = useState<NarrativeItem[]>([]);
  const [candidates, setCandidates] = useState<ResearchCandidate[]>([]);
  const [pursuitCandidates, setPursuitCandidates] = useState<PursuitCandidate[]>([]);
  const [llmStatus, setLlmStatus] = useState<LlmStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<'ingest' | 'analysis' | 'full_scan' | 'universe_scan' | 'triage_to_prediction' | null>(null);
  const [profile, setProfile] = useState<'conservative_scan' | 'balanced_scan' | 'broad_scan'>('balanced_scan');

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryRes, boardRes, sourcesRes, itemsRes, candidatesRes, pursuitRes, llmRes] = await Promise.all([
        getResearchSummary(),
        getResearchBoardSummary(),
        getResearchSources(),
        getResearchItems(),
        getResearchCandidates(),
        getPursuitCandidates(),
        getLlmStatus(),
      ]);
      setSummary(summaryRes);
      setBoardSummary(boardRes);
      setSources(sourcesRes);
      setItems(itemsRes);
      setCandidates(candidatesRes);
      setPursuitCandidates(pursuitRes);
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

  const runUniverse = async () => {
    setActionLoading('universe_scan');
    try {
      await runUniverseScan({ filter_profile: profile });
      await load();
    } finally {
      setActionLoading(null);
    }
  };

  const triggerTriageToPrediction = async () => {
    if (!boardSummary?.latest_scan) return;
    setActionLoading('triage_to_prediction');
    try {
      await runTriageToPrediction({ run_id: boardSummary.latest_scan.id, limit: 10 });
      await load();
      navigate('/agents');
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
        description="Narrative ingestion + local analysis + universe scanner/triage board for paper/demo-only market pursuit decisions."
        actions={(
          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
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
        <SectionCard eyebrow="Universe scanner" title="Market triage board" description="Scan a broad market universe and triage by tradability + timing + narrative context.">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.75rem' }}>
            <label htmlFor="scan_profile"><strong>Profile:</strong></label>
            <select id="scan_profile" value={profile} onChange={(event) => setProfile(event.target.value as typeof profile)}>
              <option value="conservative_scan">conservative_scan</option>
              <option value="balanced_scan">balanced_scan</option>
              <option value="broad_scan">broad_scan</option>
            </select>
            <button type="button" className="secondary-button" disabled={actionLoading === 'universe_scan'} onClick={() => void runUniverse()}>
              {actionLoading === 'universe_scan' ? 'Running universe scan...' : 'Run universe scan'}
            </button>
            <button
              type="button"
              className="secondary-button"
              disabled={!boardSummary?.latest_scan || actionLoading === 'triage_to_prediction'}
              onClick={() => void triggerTriageToPrediction()}
            >
              {actionLoading === 'triage_to_prediction' ? 'Handing off...' : 'Run triage → prediction'}
            </button>
          </div>
          {boardSummary?.latest_scan ? (
            <div className="system-metadata-grid">
              <div><strong>Latest scan:</strong> #{boardSummary.latest_scan.id}</div>
              <div><strong>Status:</strong> <StatusBadge tone={triageTone(boardSummary.latest_scan.status)}>{boardSummary.latest_scan.status.toUpperCase()}</StatusBadge></div>
              <div><strong>Profile:</strong> {boardSummary.latest_scan.filter_profile}</div>
              <div><strong>Finished:</strong> {fmtDate(boardSummary.latest_scan.finished_at)}</div>
            </div>
          ) : (
            <p>Run a universe scan to triage markets.</p>
          )}
          <div className="system-metadata-grid" style={{ marginTop: '0.75rem' }}>
            <div><strong>Markets considered:</strong> {boardSummary?.markets_considered ?? 0}</div>
            <div><strong>Filtered out:</strong> {boardSummary?.markets_filtered_out ?? 0}</div>
            <div><strong>Shortlisted:</strong> {boardSummary?.markets_shortlisted ?? 0}</div>
            <div><strong>Watchlist:</strong> {boardSummary?.markets_watchlist ?? 0}</div>
          </div>
          <div style={{ marginTop: '0.75rem' }}>
            <strong>Top exclusion reasons:</strong>{' '}
            {(boardSummary?.top_exclusion_reasons?.length ?? 0) > 0
              ? boardSummary?.top_exclusion_reasons.map(([reason, count]) => `${reason} (${count})`).join(', ')
              : 'No exclusions yet.'}
          </div>
        </SectionCard>

        <SectionCard eyebrow="Pursuit board" title="Markets worth pursuing" description="SHORTLISTED/WATCH triage outputs that can feed prediction and risk pipelines.">
          {pursuitCandidates.length === 0 ? (
            <EmptyState eyebrow="No pursuit candidates" title="No triaged markets yet" description="Run a universe scan to triage markets." />
          ) : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Market</th><th>Provider</th><th>Liquidity</th><th>Volume24h</th><th>Time to resolution</th><th>Narrative</th><th>Source mix</th><th>Triage score</th><th>Status</th><th>Rationale</th><th>Actions</th></tr></thead>
                <tbody>
                  {pursuitCandidates.map((candidate) => (
                    <tr key={candidate.id}>
                      <td>{candidate.market_title}</td>
                      <td>{candidate.provider_slug}</td>
                      <td>{candidate.liquidity ?? '—'}</td>
                      <td>{candidate.volume_24h ?? '—'}</td>
                      <td>{candidate.time_to_resolution_hours != null ? `${candidate.time_to_resolution_hours}h` : '—'}</td>
                      <td><StatusBadge tone={sentimentTone(candidate.narrative_direction)}>{candidate.narrative_direction}</StatusBadge></td>
                      <td>{candidate.source_mix}</td>
                      <td>{candidate.triage_score}</td>
                      <td><StatusBadge tone={triageTone(candidate.triage_status)}>{candidate.triage_status.toUpperCase()}</StatusBadge></td>
                      <td>{candidate.rationale}</td>
                      <td>
                        <button type="button" className="link-button" onClick={() => navigate(`/prediction?market_id=${candidate.market}`)}>Score in prediction</button>
                        {' · '}
                        <button type="button" className="link-button" onClick={() => navigate(`/markets/${candidate.market_slug}`)}>Open market</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Status" title="Research scan summary" description="MVP pipeline: source ingest → analysis → market linking → shortlist.">
          <div className="system-metadata-grid">
            <div><strong>Enabled sources:</strong> {summary?.source_count ?? 0}</div>
            <div><strong>Narrative items:</strong> {summary?.item_count ?? 0}</div>
            <div><strong>Analyzed items:</strong> {summary?.analyzed_count ?? 0}</div>
            <div><strong>Candidates:</strong> {summary?.candidate_count ?? 0}</div>
          </div>
          <div className="system-metadata-grid" style={{ marginTop: '0.8rem' }}>
            <div><strong>Latest run:</strong> {summary?.latest_run ? `#${summary.latest_run.id} (${summary.latest_run.status})` : 'No run yet'}</div>
            <div><strong>Last run at:</strong> {fmtDate(summary?.latest_run?.finished_at ?? summary?.latest_run?.started_at)}</div>
            <div><strong>LLM status:</strong> {llmStatus?.status ?? 'unknown'}</div>
            <div><strong>LLM note:</strong> {llmStatus?.message ?? 'Unavailable.'}</div>
          </div>
        </SectionCard>

        <SectionCard eyebrow="Sources" title="Configured narrative sources" description="RSS/news, Reddit, and optional X/Twitter adapters.">
          {sources.length === 0 ? (
            <EmptyState eyebrow="No sources" title="No narrative sources configured" description="Add an RSS, Reddit, or X/Twitter source and run ingest first." />
          ) : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Name</th><th>Type</th><th>Detail</th><th>Status</th></tr></thead>
                <tbody>
                  {sources.map((source) => (
                    <tr key={source.id}>
                      <td>{source.name}</td>
                      <td><StatusBadge tone={sourceBadge(source.source_type)}>{source.source_type.toUpperCase()}</StatusBadge></td>
                      <td>{source.source_type === 'reddit' ? `r/${String(source.metadata?.subreddit ?? source.category ?? source.slug)}` : source.source_type === 'twitter' ? `${String(source.metadata?.query ?? source.metadata?.account ?? source.metadata?.hashtag ?? source.slug)}` : source.feed_url}</td>
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
            <EmptyState eyebrow="No items" title="No narrative items yet" description="Add an RSS, Reddit, or X/Twitter source and run ingest first." />
          ) : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Title</th><th>Source</th><th>Type</th><th>Published</th><th>Sentiment</th><th>Confidence</th><th>Linked markets</th></tr></thead>
                <tbody>
                  {topItems.map((item) => (
                    <tr key={item.id}>
                      <td><a href={item.url} target="_blank" rel="noreferrer">{item.title}</a></td>
                      <td>{item.source_name}</td>
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
                <thead><tr><th>Market</th><th>Narrative direction</th><th>Source mix</th><th>Relation</th><th>Priority</th><th>Precedent</th><th>Thesis</th></tr></thead>
                <tbody>
                  {candidates.map((candidate) => (
                    <tr key={candidate.id}>
                      {(() => {
                        const precedent = (candidate.metadata?.precedent_context ?? {}) as Record<string, unknown>;
                        const warnings = (precedent.warnings as string[] | undefined) ?? [];
                        return (
                          <>
                      <td>{candidate.market_title}</td>
                      <td><StatusBadge tone={sentimentTone(candidate.sentiment_direction)}>{candidate.sentiment_direction}</StatusBadge></td>
                      <td><StatusBadge tone={sourceMixBadge(candidate.source_mix)}>{candidate.source_mix.toUpperCase()}</StatusBadge></td>
                      <td><StatusBadge tone={relationTone(candidate.relation)}>{candidate.relation}</StatusBadge></td>
                      <td>{candidate.priority}</td>
                      <td>
                        {precedent.precedent_aware ? (
                          <div style={{ display: 'grid', gap: '0.25rem' }}>
                            <StatusBadge tone="pending">PRECEDENT_AWARE</StatusBadge>
                            <small>{warnings.join(', ') || 'No strong precedents found for this case.'}</small>
                          </div>
                        ) : '—'}
                      </td>
                      <td>{candidate.short_thesis}</td>
                          </>
                        );
                      })()}
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

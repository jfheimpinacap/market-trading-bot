import { useCallback, useEffect, useMemo, useState } from 'react';

import { EmptyState } from '../components/EmptyState';
import { PageHeader } from '../components/PageHeader';
import { SectionCard } from '../components/SectionCard';
import { StatusBadge } from '../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../components/markets/DataStateWrapper';
import { navigate } from '../lib/router';
import {
  getConsensusRecommendations,
  getConsensusRecords,
  getConsensusSummary,
  getDivergenceRecords,
  getResearchHandoffPriorities,
  getScanClusters,
  getScanRecommendations,
  getScanSignals,
  getScanSummary,
  runConsensusReview,
  runScanAgent,
} from '../services/scanAgent';
import type {
  ConsensusSummary,
  NarrativeCluster,
  NarrativeConsensusRecommendation,
  NarrativeConsensusRecord,
  NarrativeMarketDivergenceRecord,
  NarrativeSignal,
  ResearchHandoffPriority,
  ScanRecommendation,
  ScanSummary,
} from '../types/scanAgent';

const tone = (value: string): 'ready' | 'pending' | 'offline' | 'neutral' => {
  const normalized = value.toUpperCase();
  if (['SHORTLISTED', 'CONFIRMED_MULTI_SOURCE', 'SEND_TO_RESEARCH_TRIAGE', 'SEND_TO_PREDICTION_CONTEXT'].includes(normalized)) return 'ready';
  if (['WATCH', 'EMERGING', 'KEEP_ON_WATCHLIST', 'REQUIRE_MANUAL_REVIEW', 'CANDIDATE'].includes(normalized)) return 'pending';
  if (['IGNORE', 'NOISY', 'STALE', 'IGNORE_NOISE'].includes(normalized)) return 'offline';
  return 'neutral';
};

export function ScanAgentPage() {
  const [summary, setSummary] = useState<ScanSummary | null>(null);
  const [signals, setSignals] = useState<NarrativeSignal[]>([]);
  const [clusters, setClusters] = useState<NarrativeCluster[]>([]);
  const [recommendations, setRecommendations] = useState<ScanRecommendation[]>([]);
  const [consensusSummary, setConsensusSummary] = useState<ConsensusSummary | null>(null);
  const [consensusRecords, setConsensusRecords] = useState<NarrativeConsensusRecord[]>([]);
  const [divergenceRecords, setDivergenceRecords] = useState<NarrativeMarketDivergenceRecord[]>([]);
  const [handoffPriorities, setHandoffPriorities] = useState<ResearchHandoffPriority[]>([]);
  const [consensusRecommendations, setConsensusRecommendations] = useState<NarrativeConsensusRecommendation[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [recommendationFilter, setRecommendationFilter] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [runLoading, setRunLoading] = useState(false);
  const [consensusRunLoading, setConsensusRunLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryRes, signalsRes, clustersRes, recommendationsRes, consensusSummaryRes, consensusRecordsRes, divergenceRes, prioritiesRes, consensusRecommendationsRes] = await Promise.all([
        getScanSummary(),
        getScanSignals(statusFilter ? { status: statusFilter } : undefined),
        getScanClusters(),
        getScanRecommendations(recommendationFilter ? { recommendation_type: recommendationFilter } : undefined),
        getConsensusSummary(),
        getConsensusRecords(),
        getDivergenceRecords(),
        getResearchHandoffPriorities(),
        getConsensusRecommendations(),
      ]);
      setSummary(summaryRes);
      setSignals(signalsRes);
      setClusters(clustersRes);
      setRecommendations(recommendationsRes);
      setConsensusSummary(consensusSummaryRes);
      setConsensusRecords(consensusRecordsRes);
      setDivergenceRecords(divergenceRes);
      setHandoffPriorities(prioritiesRes);
      setConsensusRecommendations(consensusRecommendationsRes);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Could not load scan agent data.');
    } finally {
      setLoading(false);
    }
  }, [recommendationFilter, statusFilter]);

  useEffect(() => {
    void load();
  }, [load]);

  const runScan = async () => {
    setRunLoading(true);
    try {
      await runScanAgent();
      await load();
    } finally {
      setRunLoading(false);
    }
  };
  const runConsensus = async () => {
    setConsensusRunLoading(true);
    try {
      await runConsensusReview();
      await load();
    } finally {
      setConsensusRunLoading(false);
    }
  };

  const topSignals = useMemo(() => signals.slice(0, 25), [signals]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Parallel source intelligence"
        title="/scan-agent"
        description="Local-first, single-user, paper-only scan→research hardening. Consolidates RSS/Reddit/X, detects cross-source consensus/conflict, scores narrative-vs-market divergence, and prioritizes auditable research handoff without live execution."
        actions={<div className="button-row"><button type="button" className="secondary-button" onClick={() => navigate('/research-agent')}>Open research</button><button type="button" className="secondary-button" onClick={() => navigate('/prediction')}>Open prediction</button><button type="button" className="secondary-button" onClick={() => navigate('/cockpit')}>Open cockpit</button><button type="button" className="secondary-button" onClick={() => navigate('/trace')}>Open trace</button><button type="button" className="primary-button" disabled={runLoading} onClick={() => void runScan()}>{runLoading ? 'Running scan...' : 'Run scan'}</button><button type="button" className="primary-button" disabled={consensusRunLoading} onClick={() => void runConsensus()}>{consensusRunLoading ? 'Running consensus review...' : 'Run consensus review'}</button></div>}
      />

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <div className="content-grid content-grid--three-columns">
          <SectionCard eyebrow="Summary" title="Source intake" description="Recent scan run and source counts.">
            <ul className="key-value-list">
              <li><span>RSS items</span><strong>{summary?.latest_run?.source_counts?.rss_count ?? 0}</strong></li>
              <li><span>Reddit items</span><strong>{summary?.latest_run?.source_counts?.reddit_count ?? 0}</strong></li>
              <li><span>X items</span><strong>{summary?.latest_run?.source_counts?.x_count ?? 0}</strong></li>
              <li><span>Deduped items</span><strong>{summary?.latest_run?.deduped_item_count ?? 0}</strong></li>
              <li><span>Clusters</span><strong>{summary?.latest_run?.clustered_count ?? 0}</strong></li>
              <li><span>Shortlisted signals</span><strong>{summary?.shortlisted_signal_count ?? 0}</strong></li>
            </ul>
          </SectionCard>
          <SectionCard eyebrow="Signal states" title="Filter health" description="WATCH and IGNORE are valid states for conservative scan discipline.">
            <ul className="key-value-list">
              <li><span>Total signals</span><strong>{summary?.signal_count ?? 0}</strong></li>
              <li><span>Watch signals</span><strong>{summary?.watch_signal_count ?? 0}</strong></li>
              <li><span>Ignored signals</span><strong>{summary?.ignored_signal_count ?? 0}</strong></li>
              <li><span>Runs</span><strong>{summary?.run_count ?? 0}</strong></li>
            </ul>
          </SectionCard>
          <SectionCard eyebrow="Filters" title="Manual controls" description="Conservative recommendation-first filtering.">
            <label htmlFor="signal-status"><strong>Signal status</strong></label>
            <select id="signal-status" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
              <option value="">all</option><option value="shortlisted">shortlisted</option><option value="candidate">candidate</option><option value="watch">watch</option><option value="ignore">ignore</option>
            </select>
            <label htmlFor="rec-type" style={{ marginTop: '0.75rem', display: 'block' }}><strong>Recommendation</strong></label>
            <select id="rec-type" value={recommendationFilter} onChange={(event) => setRecommendationFilter(event.target.value)}>
              <option value="">all</option><option value="send_to_research_triage">send_to_research_triage</option><option value="send_to_prediction_context">send_to_prediction_context</option><option value="keep_on_watchlist">keep_on_watchlist</option><option value="ignore_noise">ignore_noise</option><option value="require_manual_review">require_manual_review</option>
            </select>
            <div style={{ marginTop: '0.75rem' }}><button type="button" className="secondary-button" onClick={() => void load()}>Apply filters</button></div>
          </SectionCard>
        </div>

        <SectionCard eyebrow="Narrative signals" title="Narrative-to-market edge board" description="Prioritized handoff signals for research triage / prediction context.">
          {topSignals.length === 0 ? (
            <EmptyState
              eyebrow="No signals yet"
              title="No narrative scan signals are available yet"
              description="Run a scan to generate source intelligence."
            />
          ) : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Canonical label</th><th>Source mix</th><th>Direction</th><th>Novelty</th><th>Intensity</th><th>Divergence</th><th>Total score</th><th>Status</th><th>Actions</th></tr></thead>
                <tbody>
                  {topSignals.map((signal) => (
                    <tr key={signal.id}>
                      <td>{signal.canonical_label}</td>
                      <td>{(signal.source_mix.source_types ?? []).join(', ') || '—'}</td>
                      <td>{signal.direction}</td>
                      <td>{signal.novelty_score}</td>
                      <td>{signal.intensity_score}</td>
                      <td>{signal.market_divergence_score}</td>
                      <td>{signal.total_signal_score}</td>
                      <td><StatusBadge tone={tone(signal.status)}>{signal.status.toUpperCase()}</StatusBadge></td>
                      <td><button type="button" className="link-button" onClick={() => navigate('/research')}>Research</button>{' · '}<button type="button" className="link-button" onClick={() => navigate(signal.linked_market_slug ? `/markets/${signal.linked_market_slug}` : '/markets')}>Market</button>{' · '}<button type="button" className="link-button" onClick={() => navigate('/prediction')}>Prediction</button>{' · '}<button type="button" className="link-button" onClick={() => navigate('/trace')}>Trace</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Narrative Consensus & Market Divergence" title="Consensus-to-research handoff hardening" description="Paper-only, cross-source consensus, divergence-aware, and explicitly non-live-execution.">
          <div className="content-grid content-grid--three-columns">
            <ul className="key-value-list">
              <li><span>Signals considered</span><strong>{consensusSummary?.signals_considered ?? 0}</strong></li>
              <li><span>Clusters considered</span><strong>{consensusSummary?.clusters_considered ?? 0}</strong></li>
            </ul>
            <ul className="key-value-list">
              <li><span>Strong consensus</span><strong>{consensusSummary?.strong_consensus_count ?? 0}</strong></li>
              <li><span>Conflicted narratives</span><strong>{consensusSummary?.conflicted_count ?? 0}</strong></li>
            </ul>
            <ul className="key-value-list">
              <li><span>High divergence</span><strong>{consensusSummary?.high_divergence_count ?? 0}</strong></li>
              <li><span>Ready for research</span><strong>{consensusSummary?.ready_for_research_count ?? 0}</strong></li>
            </ul>
          </div>
        </SectionCard>

        <div className="content-grid content-grid--two-columns">
          <SectionCard eyebrow="Consensus records" title="Cross-source narrative consensus" description="Transparent narrative consolidation by cluster/topic.">
            <div className="table-wrapper"><table className="data-table"><thead><tr><th>Topic</th><th>Source mix</th><th>Consensus</th><th>Sentiment</th><th>Intensity</th><th>Novelty</th><th>Persistence</th><th>Confidence</th></tr></thead><tbody>{consensusRecords.slice(0, 15).map((item) => <tr key={item.id}><td>{item.topic_label}</td><td>{((item.source_mix.source_types as string[] | undefined) ?? []).join(', ') || '—'}</td><td>{item.consensus_state}</td><td>{item.sentiment_direction}</td><td>{item.intensity_score}</td><td>{item.novelty_score}</td><td>{item.persistence_score}</td><td>{item.confidence_score}</td></tr>)}</tbody></table></div>
          </SectionCard>
          <SectionCard eyebrow="Divergence records" title="Narrative vs market divergence" description="Compare source consensus against market-implied probability.">
            <div className="table-wrapper"><table className="data-table"><thead><tr><th>Market</th><th>Narrative bias</th><th>Market probability</th><th>Divergence state</th><th>Divergence score</th><th>Summary</th></tr></thead><tbody>{divergenceRecords.slice(0, 15).map((item) => <tr key={item.id}><td>{item.linked_market_title || '—'}</td><td>{item.narrative_bias}</td><td>{item.market_probability ?? '—'}</td><td>{item.divergence_state}</td><td>{item.divergence_score}</td><td>{item.market_context_summary}</td></tr>)}</tbody></table></div>
          </SectionCard>
        </div>

        <div className="content-grid content-grid--two-columns">
          <SectionCard eyebrow="Research handoff priorities" title="Scan→research prioritization queue" description="Prioritized intake that does not replace research-agent triage authority.">
            <div className="table-wrapper"><table className="data-table"><thead><tr><th>Market/topic</th><th>Priority bucket</th><th>Handoff status</th><th>Reason codes</th><th>Score</th><th>Summary</th></tr></thead><tbody>{handoffPriorities.slice(0, 20).map((item) => <tr key={item.id}><td>{item.linked_market_title || item.topic_label || '—'}</td><td>{item.priority_bucket}</td><td>{item.handoff_status}</td><td>{item.priority_reason_codes.join(', ') || '—'}</td><td>{item.priority_score}</td><td>{item.handoff_summary}</td></tr>)}</tbody></table></div>
          </SectionCard>
          <SectionCard eyebrow="Consensus recommendations" title="Conservative recommendation outputs" description="Explicit recommendation types with rationale, blockers, and confidence.">
            <div className="table-wrapper"><table className="data-table"><thead><tr><th>Type</th><th>Rationale</th><th>Reason codes</th><th>Blockers</th><th>Confidence</th></tr></thead><tbody>{consensusRecommendations.slice(0, 20).map((item) => <tr key={item.id}><td>{item.recommendation_type}</td><td>{item.rationale}</td><td>{item.reason_codes.join(', ') || '—'}</td><td>{item.blockers.join(', ') || '—'}</td><td>{item.confidence}</td></tr>)}</tbody></table></div>
          </SectionCard>
        </div>

        <div className="content-grid content-grid--two-columns">
          <SectionCard eyebrow="Clusters" title="Narrative clusters" description="Deduplicated, grouped narrative themes across sources.">
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Topic</th><th>Headline</th><th>Items</th><th>Sources</th><th>Status</th></tr></thead>
                <tbody>
                  {clusters.slice(0, 20).map((cluster) => (
                    <tr key={cluster.id}><td>{cluster.canonical_topic}</td><td>{cluster.representative_headline}</td><td>{cluster.item_count}</td><td>{cluster.source_types.join(', ')}</td><td><StatusBadge tone={tone(cluster.cluster_status)}>{cluster.cluster_status.toUpperCase()}</StatusBadge></td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          </SectionCard>

          <SectionCard eyebrow="Recommendations" title="Handoff recommendations" description="Recommendation-first outputs for triage and prediction context.">
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Type</th><th>Signal</th><th>Rationale</th><th>Reason codes</th><th>Confidence</th></tr></thead>
                <tbody>
                  {recommendations.slice(0, 24).map((recommendation) => (
                    <tr key={recommendation.id}><td><StatusBadge tone={tone(recommendation.recommendation_type)}>{recommendation.recommendation_type.toUpperCase()}</StatusBadge></td><td>{recommendation.target_signal_label || '—'}</td><td>{recommendation.rationale}</td><td>{recommendation.reason_codes.join(', ') || '—'}</td><td>{recommendation.confidence}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          </SectionCard>
        </div>
      </DataStateWrapper>
    </div>
  );
}

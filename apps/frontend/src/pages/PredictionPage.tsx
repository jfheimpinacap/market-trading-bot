import { useCallback, useEffect, useMemo, useState } from 'react';
import { EmptyState } from '../components/EmptyState';
import { PageHeader } from '../components/PageHeader';
import { SectionCard } from '../components/SectionCard';
import { StatusBadge } from '../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../components/markets/DataStateWrapper';
import { navigate } from '../lib/router';
import { getMarkets } from '../services/markets';
import {
  getPredictionProfiles,
  getPredictionScores,
  getPredictionSummary,
  scoreMarketPrediction,
} from '../services/prediction';
import { getLlmStatus } from '../services/llm';
import type { MarketListItem } from '../types/markets';
import type { PredictionProfile, PredictionScore, PredictionSummary } from '../types/prediction';

function fmtPct(value?: string | null) {
  if (!value) return '—';
  const num = Number(value);
  if (Number.isNaN(num)) return value;
  return `${(num * 100).toFixed(2)}%`;
}

function edgeTone(label: string) {
  if (label === 'positive') return 'ready';
  if (label === 'negative') return 'offline';
  return 'neutral';
}

function confidenceTone(level: string) {
  if (level === 'high') return 'ready';
  if (level === 'medium') return 'pending';
  return 'neutral';
}

export function PredictionPage() {
  const initialMarketId = useMemo(() => {
    const params = new URLSearchParams(window.location.search);
    const marketId = Number(params.get('market_id'));
    return Number.isFinite(marketId) && marketId > 0 ? marketId : null;
  }, []);
  const [profiles, setProfiles] = useState<PredictionProfile[]>([]);
  const [scores, setScores] = useState<PredictionScore[]>([]);
  const [summary, setSummary] = useState<PredictionSummary | null>(null);
  const [markets, setMarkets] = useState<MarketListItem[]>([]);
  const [selectedMarketId, setSelectedMarketId] = useState<number | null>(initialMarketId);
  const [selectedProfile, setSelectedProfile] = useState<string>('heuristic_baseline');
  const [result, setResult] = useState<PredictionScore | null>(null);
  const [llmReachable, setLlmReachable] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [scoring, setScoring] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [profilesRes, scoresRes, summaryRes, marketsRes, llmRes] = await Promise.all([
        getPredictionProfiles(),
        getPredictionScores(),
        getPredictionSummary(),
        getMarkets({ ordering: '-updated_at' }),
        getLlmStatus(),
      ]);
      setProfiles(profilesRes);
      setScores(scoresRes);
      setSummary(summaryRes);
      setMarkets(marketsRes.slice(0, 200));
      setLlmReachable(Boolean(llmRes.reachable));
      if (!selectedMarketId && marketsRes.length > 0) {
        setSelectedMarketId(marketsRes[0].id);
      }
      if (!result && summaryRes.latest_score) {
        setResult(summaryRes.latest_score);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load prediction agent data.');
    } finally {
      setLoading(false);
    }
  }, [result, selectedMarketId]);

  useEffect(() => {
    void load();
  }, [load]);

  const runScore = async () => {
    if (!selectedMarketId) {
      setError('Select a market first.');
      return;
    }
    setScoring(true);
    setError(null);
    try {
      const score = await scoreMarketPrediction({
        market_id: selectedMarketId,
        profile_slug: selectedProfile || undefined,
        triggered_by: 'prediction_page',
      });
      setResult(score);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Scoring failed.');
    } finally {
      setScoring(false);
    }
  };

  const recentScores = useMemo(() => scores.slice(0, 25), [scores]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Prediction agent"
        title="Prediction"
        description="System probability + market implied probability + auditable edge scoring for paper/demo proposals only. No real-money and no real execution."
        actions={<button type="button" className="secondary-button" onClick={() => navigate('/proposals')}>Open Proposals</button>}
      />

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Overview" title="Prediction summary" description="MVP foundation: feature snapshot → profile scoring → basic calibration → edge/confidence output.">
          <div className="system-metadata-grid">
            <div><strong>Profiles:</strong> {summary?.profile_count ?? 0}</div>
            <div><strong>Total scores:</strong> {summary?.total_scores ?? 0}</div>
            <div><strong>Average edge:</strong> {fmtPct(summary?.avg_edge)}</div>
            <div><strong>Average confidence:</strong> {fmtPct(summary?.avg_confidence)}</div>
          </div>
          {llmReachable === false ? (
            <p style={{ marginTop: '0.75rem' }}><strong>Degraded narrative mode:</strong> prediction scoring still runs using market/momentum features if LLM-backed narrative refresh is unavailable.</p>
          ) : null}
        </SectionCard>

        <SectionCard eyebrow="Profiles" title="Model profiles" description="Switch profile to compare baseline vs narrative/momentum emphasis.">
          {profiles.length === 0 ? (
            <EmptyState eyebrow="No profiles" title="No prediction profiles available" description="Prediction profiles will auto-seed after backend initialization." />
          ) : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Slug</th><th>Description</th><th>Narrative</th><th>Learning</th></tr></thead>
                <tbody>
                  {profiles.map((profile) => (
                    <tr key={profile.id}>
                      <td>{profile.slug}</td>
                      <td>{profile.description}</td>
                      <td>{profile.use_narrative ? 'on' : 'off'}</td>
                      <td>{profile.use_learning ? 'on' : 'off'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Score market" title="Run prediction scoring" description="Select a market + profile to compute system probability and edge.">
          <div style={{ display: 'grid', gap: '0.75rem', gridTemplateColumns: '2fr 1fr auto' }}>
            <select value={selectedMarketId ?? ''} onChange={(e) => setSelectedMarketId(Number(e.target.value))}>
              {markets.map((market) => <option key={market.id} value={market.id}>{market.title}</option>)}
            </select>
            <select value={selectedProfile} onChange={(e) => setSelectedProfile(e.target.value)}>
              {profiles.map((profile) => <option key={profile.id} value={profile.slug}>{profile.slug}</option>)}
            </select>
            <button type="button" className="secondary-button" onClick={() => void runScore()} disabled={scoring || !selectedMarketId}>
              {scoring ? 'Scoring...' : 'Score market'}
            </button>
          </div>
        </SectionCard>

        <SectionCard eyebrow="Result" title="Latest prediction result" description="Output contract consumed by proposal context: probability, edge, confidence, rationale.">
          {!result ? (
            <EmptyState eyebrow="No score" title="Run a prediction score for a market first." description="The result card appears after successful scoring." />
          ) : (
            <>
              <div className="system-metadata-grid">
                <div><strong>Market:</strong> <button type="button" className="link-button" onClick={() => navigate(`/markets/${result.market_slug}`)}>{result.market_title}</button></div>
                <div><strong>Profile:</strong> {result.profile_slug}</div>
                <div><strong>System probability:</strong> {fmtPct(result.system_probability)}</div>
                <div><strong>Market probability:</strong> {fmtPct(result.market_probability)}</div>
                <div><strong>Edge:</strong> <StatusBadge tone={edgeTone(result.edge_label)}>{fmtPct(result.edge)} ({result.edge_label})</StatusBadge></div>
                <div><strong>Confidence:</strong> <StatusBadge tone={confidenceTone(result.confidence_level)}>{fmtPct(result.confidence)} ({result.confidence_level})</StatusBadge></div>
                <div><strong>Narrative contribution:</strong> {fmtPct(result.narrative_contribution)}</div>
              </div>
              <p style={{ marginTop: '0.75rem' }}><strong>Rationale:</strong> {result.rationale}</p>
            </>
          )}
        </SectionCard>

        <SectionCard eyebrow="Recent runs" title="Recent prediction scores" description="Auditable history for replay/evaluation/proposal traceability.">
          {recentScores.length === 0 ? (
            <EmptyState eyebrow="No scores" title="Run a prediction score for a market first." description="Recent scored markets appear here." />
          ) : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Market</th><th>Profile</th><th>Edge</th><th>Confidence</th><th>Created</th></tr></thead>
                <tbody>
                  {recentScores.map((score) => (
                    <tr key={score.id}>
                      <td><button type="button" className="link-button" onClick={() => navigate(`/markets/${score.market_slug}`)}>{score.market_title}</button></td>
                      <td>{score.profile_slug}</td>
                      <td><StatusBadge tone={edgeTone(score.edge_label)}>{fmtPct(score.edge)}</StatusBadge></td>
                      <td><StatusBadge tone={confidenceTone(score.confidence_level)}>{fmtPct(score.confidence)}</StatusBadge></td>
                      <td>{new Date(score.created_at).toLocaleString()}</td>
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

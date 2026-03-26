import { useCallback, useEffect, useMemo, useState } from 'react';
import { EmptyState } from '../components/EmptyState';
import { PageHeader } from '../components/PageHeader';
import { SectionCard } from '../components/SectionCard';
import { StatusBadge } from '../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../components/markets/DataStateWrapper';
import { navigate } from '../lib/router';
import { getMarkets } from '../services/markets';
import {
  activatePredictionModel,
  buildPredictionDataset,
  getPredictionModels,
  getPredictionProfiles,
  getPredictionScores,
  getPredictionSummary,
  getPredictionTrainingRuns,
  getPredictionTrainingSummary,
  scoreMarketPrediction,
  trainPredictionModel,
} from '../services/prediction';
import { getLlmStatus } from '../services/llm';
import type { MarketListItem } from '../types/markets';
import type {
  PredictionModelArtifact,
  PredictionProfile,
  PredictionScore,
  PredictionSummary,
  PredictionTrainingRun,
  PredictionTrainingSummary,
} from '../types/prediction';

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
  const [trainingSummary, setTrainingSummary] = useState<PredictionTrainingSummary | null>(null);
  const [trainingRuns, setTrainingRuns] = useState<PredictionTrainingRun[]>([]);
  const [models, setModels] = useState<PredictionModelArtifact[]>([]);
  const [markets, setMarkets] = useState<MarketListItem[]>([]);
  const [selectedMarketId, setSelectedMarketId] = useState<number | null>(initialMarketId);
  const [selectedProfile, setSelectedProfile] = useState<string>('heuristic_baseline');
  const [result, setResult] = useState<PredictionScore | null>(null);
  const [llmReachable, setLlmReachable] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [scoring, setScoring] = useState(false);
  const [buildingDataset, setBuildingDataset] = useState(false);
  const [training, setTraining] = useState(false);
  const [activatingModelId, setActivatingModelId] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [profilesRes, scoresRes, summaryRes, marketsRes, llmRes, trainingSummaryRes, trainingRunsRes, modelsRes] = await Promise.all([
        getPredictionProfiles(),
        getPredictionScores(),
        getPredictionSummary(),
        getMarkets({ ordering: '-updated_at' }),
        getLlmStatus(),
        getPredictionTrainingSummary(),
        getPredictionTrainingRuns(),
        getPredictionModels(),
      ]);
      setProfiles(profilesRes);
      setScores(scoresRes);
      setSummary(summaryRes);
      setTrainingSummary(trainingSummaryRes);
      setTrainingRuns(trainingRunsRes.slice(0, 20));
      setModels(modelsRes.slice(0, 20));
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

  const runBuildDataset = async () => {
    setBuildingDataset(true);
    setError(null);
    try {
      await buildPredictionDataset({ name: 'ui_dataset', horizon_hours: 24 });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Dataset build failed.');
    } finally {
      setBuildingDataset(false);
    }
  };

  const runTraining = async () => {
    if (!trainingSummary?.latest_dataset?.id) {
      setError('Build dataset first.');
      return;
    }
    setTraining(true);
    setError(null);
    try {
      await trainPredictionModel({ dataset_run_id: trainingSummary.latest_dataset.id, model_name: 'xgboost_baseline' });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Training failed.');
    } finally {
      setTraining(false);
    }
  };

  const runActivateModel = async (id: number) => {
    setActivatingModelId(id);
    setError(null);
    try {
      await activatePredictionModel(id);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Activation failed.');
    } finally {
      setActivatingModelId(null);
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
        <SectionCard eyebrow="Overview" title="Prediction summary" description="MVP foundation: feature snapshot → profile scoring → calibrated trained model (if active) → fallback heuristic.">
          <div className="system-metadata-grid">
            <div><strong>Profiles:</strong> {summary?.profile_count ?? 0}</div>
            <div><strong>Total scores:</strong> {summary?.total_scores ?? 0}</div>
            <div><strong>Average edge:</strong> {fmtPct(summary?.avg_edge)}</div>
            <div><strong>Average confidence:</strong> {fmtPct(summary?.avg_confidence)}</div>
          </div>
          <p style={{ marginTop: '0.75rem' }}>
            <strong>Active runtime model:</strong>{' '}
            {trainingSummary?.active_model ? `${trainingSummary.active_model.name} (${trainingSummary.active_model.version})` : 'Heuristic fallback (no active trained model)'}
          </p>
          {llmReachable === false ? (
            <p style={{ marginTop: '0.75rem' }}><strong>Degraded narrative mode:</strong> prediction scoring still runs using market/momentum features if LLM-backed narrative refresh is unavailable.</p>
          ) : null}
        </SectionCard>

        <SectionCard eyebrow="Training" title="Dataset + training controls" description="Offline-only local pipeline. Build reproducible dataset, run XGBoost + sigmoid calibration, activate model.">
          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
            <button type="button" className="secondary-button" onClick={() => void runBuildDataset()} disabled={buildingDataset}>{buildingDataset ? 'Building dataset...' : 'Build dataset'}</button>
            <button type="button" className="secondary-button" onClick={() => void runTraining()} disabled={training || !trainingSummary?.latest_dataset}>{training ? 'Training...' : 'Train model'}</button>
          </div>
          <div className="system-metadata-grid" style={{ marginTop: '0.75rem' }}>
            <div><strong>Latest dataset rows:</strong> {trainingSummary?.latest_dataset?.rows_built ?? 0}</div>
            <div><strong>Label:</strong> {trainingSummary?.latest_dataset?.label_definition ?? '—'}</div>
            <div><strong>Feature set:</strong> {trainingSummary?.latest_dataset?.feature_set_version ?? '—'}</div>
            <div><strong>Models total:</strong> {trainingSummary?.models_total ?? 0}</div>
          </div>
        </SectionCard>

        <SectionCard eyebrow="Model registry" title="Model artifacts" description="Activate one model at a time for prediction runtime. Risk/policy/safety are unchanged.">
          {models.length === 0 ? (
            <EmptyState eyebrow="No models" title="No trained model artifacts yet" description="Build dataset and run training to register the first XGBoost artifact." />
          ) : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Name</th><th>Type</th><th>Version</th><th>Accuracy</th><th>Active</th><th /></tr></thead>
                <tbody>
                  {models.map((model) => (
                    <tr key={model.id}>
                      <td>{model.name}</td>
                      <td>{model.model_type}</td>
                      <td>{model.version}</td>
                      <td>{String(model.validation_metrics?.accuracy ?? '—')}</td>
                      <td>{model.is_active ? 'yes' : 'no'}</td>
                      <td>
                        <button type="button" className="link-button" disabled={model.is_active || activatingModelId === model.id} onClick={() => void runActivateModel(model.id)}>
                          {activatingModelId === model.id ? 'Activating...' : model.is_active ? 'Active' : 'Activate'}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Training runs" title="Recent training runs" description="Validation metrics (accuracy, log loss, brier score) and calibration status.">
          {trainingRuns.length === 0 ? (
            <EmptyState eyebrow="No runs" title="No training runs yet" description="Train a model to see validation reports and artifact creation events." />
          ) : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>ID</th><th>Status</th><th>Rows</th><th>Accuracy</th><th>Log loss</th><th>Finished</th></tr></thead>
                <tbody>
                  {trainingRuns.map((run) => (
                    <tr key={run.id}>
                      <td>{run.id}</td>
                      <td>{run.status}</td>
                      <td>{run.rows_used}</td>
                      <td>{String(run.validation_summary?.accuracy ?? '—')}</td>
                      <td>{String(run.validation_summary?.log_loss ?? '—')}</td>
                      <td>{run.finished_at ? new Date(run.finished_at).toLocaleString() : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Score market" title="Run prediction scoring" description="Select a market + profile to compute calibrated system probability and edge.">
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
                <div><strong>Model used:</strong> {result.model_profile_used}</div>
                <div><strong>System probability:</strong> {fmtPct(result.system_probability)}</div>
                <div><strong>Market probability:</strong> {fmtPct(result.market_probability)}</div>
                <div><strong>Edge:</strong> <StatusBadge tone={edgeTone(result.edge_label)}>{fmtPct(result.edge)} ({result.edge_label})</StatusBadge></div>
                <div><strong>Confidence:</strong> <StatusBadge tone={confidenceTone(result.confidence_level)}>{fmtPct(result.confidence)} ({result.confidence_level})</StatusBadge></div>
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

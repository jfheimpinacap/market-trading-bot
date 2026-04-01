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
  compareModels,
  getActiveModelRecommendation,
  getModelComparisons,
  getModelGovernanceSummary,
  getModelProfiles,
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
import {
  getPredictionRuntimeAssessments,
  getPredictionRuntimeRecommendations,
  getPredictionRuntimeSummary,
  runPredictionRuntimeReview,
  getPredictionIntakeSummary,
  getPredictionIntakeCandidates,
  getPredictionConvictionReviews,
  getPredictionRiskHandoffs,
  getPredictionIntakeRecommendations,
  runPredictionIntakeReview,
} from '../services/predictionRuntime';
import type { MarketListItem } from '../types/markets';
import type {
  ActiveModelRecommendation,
  ModelComparisonRun,
  ModelEvaluationProfile,
  ModelGovernanceSummary,
  PredictionModelArtifact,
  PredictionProfile,
  PredictionRuntimeAssessment,
  PredictionRuntimeRecommendation,
  PredictionRuntimeSummary,
  PredictionIntakeSummary,
  PredictionIntakeCandidate,
  PredictionConvictionReview,
  PredictionRiskHandoff,
  PredictionIntakeRecommendation,
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
  const [modelProfiles, setModelProfiles] = useState<ModelEvaluationProfile[]>([]);
  const [comparisonRuns, setComparisonRuns] = useState<ModelComparisonRun[]>([]);
  const [recommendation, setRecommendation] = useState<ActiveModelRecommendation | null>(null);
  const [governanceSummary, setGovernanceSummary] = useState<ModelGovernanceSummary | null>(null);
  const [runtimeSummary, setRuntimeSummary] = useState<PredictionRuntimeSummary | null>(null);
  const [intakeSummary, setIntakeSummary] = useState<PredictionIntakeSummary | null>(null);
  const [intakeCandidates, setIntakeCandidates] = useState<PredictionIntakeCandidate[]>([]);
  const [convictionReviews, setConvictionReviews] = useState<PredictionConvictionReview[]>([]);
  const [riskHandoffs, setRiskHandoffs] = useState<PredictionRiskHandoff[]>([]);
  const [intakeRecommendations, setIntakeRecommendations] = useState<PredictionIntakeRecommendation[]>([]);
  const [runtimeAssessments, setRuntimeAssessments] = useState<PredictionRuntimeAssessment[]>([]);
  const [runtimeRecommendations, setRuntimeRecommendations] = useState<PredictionRuntimeRecommendation[]>([]);
  const [selectedMarketId, setSelectedMarketId] = useState<number | null>(initialMarketId);
  const [selectedProfile, setSelectedProfile] = useState<string>('heuristic_baseline');
  const [comparisonBaselineKey, setComparisonBaselineKey] = useState<string>('heuristic_baseline');
  const [comparisonCandidateKey, setComparisonCandidateKey] = useState<string>('active_model');
  const [comparisonProfileSlug, setComparisonProfileSlug] = useState<string>('balanced_model_eval');
  const [comparisonScope, setComparisonScope] = useState<'demo_only' | 'real_only' | 'mixed'>('mixed');
  const [result, setResult] = useState<PredictionScore | null>(null);
  const [llmReachable, setLlmReachable] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [scoring, setScoring] = useState(false);
  const [buildingDataset, setBuildingDataset] = useState(false);
  const [training, setTraining] = useState(false);
  const [activatingModelId, setActivatingModelId] = useState<number | null>(null);
  const [comparingModels, setComparingModels] = useState(false);
  const [runningRuntimeReview, setRunningRuntimeReview] = useState(false);
  const [runningIntakeReview, setRunningIntakeReview] = useState(false);
  const [runtimeStatusFilter, setRuntimeStatusFilter] = useState<string>('');

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [profilesRes, scoresRes, summaryRes, marketsRes, llmRes, trainingSummaryRes, trainingRunsRes, modelsRes, modelProfilesRes, comparisonRunsRes, recommendationRes, governanceSummaryRes, runtimeSummaryRes, intakeSummaryRes] = await Promise.all([
        getPredictionProfiles(),
        getPredictionScores(),
        getPredictionSummary(),
        getMarkets({ ordering: '-updated_at' }),
        getLlmStatus(),
        getPredictionTrainingSummary(),
        getPredictionTrainingRuns(),
        getPredictionModels(),
        getModelProfiles(),
        getModelComparisons(),
        getActiveModelRecommendation(),
        getModelGovernanceSummary(),
        getPredictionRuntimeSummary(),
        getPredictionIntakeSummary(),
      ]);
      setProfiles(profilesRes);
      setScores(scoresRes);
      setSummary(summaryRes);
      setTrainingSummary(trainingSummaryRes);
      setTrainingRuns(trainingRunsRes.slice(0, 20));
      setModels(modelsRes.slice(0, 20));
      setModelProfiles(modelProfilesRes);
      setComparisonRuns(comparisonRunsRes.slice(0, 20));
      setRecommendation(recommendationRes);
      setGovernanceSummary(governanceSummaryRes);
      setRuntimeSummary(runtimeSummaryRes);
      setIntakeSummary(intakeSummaryRes);
      const runId = runtimeSummaryRes.latest_run?.id;
      if (runId) {
        const [assessmentsRes, recommendationsRes] = await Promise.all([
          getPredictionRuntimeAssessments({ runId, status: runtimeStatusFilter || undefined }),
          getPredictionRuntimeRecommendations({ runId }),
        ]);
        setRuntimeAssessments(assessmentsRes.slice(0, 100));
        setRuntimeRecommendations(recommendationsRes.slice(0, 100));
      } else {
        setRuntimeAssessments([]);
        setRuntimeRecommendations([]);
      }
      const intakeRunId = intakeSummaryRes.latest_run?.id;
      if (intakeRunId) {
        const [intakeCandidatesRes, convictionReviewsRes, riskHandoffsRes, intakeRecommendationsRes] = await Promise.all([
          getPredictionIntakeCandidates(intakeRunId),
          getPredictionConvictionReviews(intakeRunId),
          getPredictionRiskHandoffs(intakeRunId),
          getPredictionIntakeRecommendations(intakeRunId),
        ]);
        setIntakeCandidates(intakeCandidatesRes.slice(0, 100));
        setConvictionReviews(convictionReviewsRes.slice(0, 100));
        setRiskHandoffs(riskHandoffsRes.slice(0, 100));
        setIntakeRecommendations(intakeRecommendationsRes.slice(0, 100));
      } else {
        setIntakeCandidates([]);
        setConvictionReviews([]);
        setRiskHandoffs([]);
        setIntakeRecommendations([]);
      }
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
  }, [result, runtimeStatusFilter, selectedMarketId]);

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

  const runCompareModels = async () => {
    if (comparisonCandidateKey === 'active_model' && !trainingSummary?.active_model) {
      setError('Train and activate a candidate model first.');
      return;
    }
    setComparingModels(true);
    setError(null);
    try {
      await compareModels({
        baseline_key: comparisonBaselineKey,
        candidate_key: comparisonCandidateKey,
        profile_slug: comparisonProfileSlug,
        scope: comparisonScope,
        dataset_run_id: trainingSummary?.latest_dataset?.id,
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Model comparison failed.');
    } finally {
      setComparingModels(false);
    }
  };

  const recentScores = useMemo(() => scores.slice(0, 25), [scores]);

  const runIntakeReview = async () => {
    setRunningIntakeReview(true);
    setError(null);
    try {
      await runPredictionIntakeReview({ triggered_by: 'prediction_page_intake_review' });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Intake review failed.');
    } finally {
      setRunningIntakeReview(false);
    }
  };

  const runRuntimeReview = async () => {
    setRunningRuntimeReview(true);
    setError(null);
    try {
      await runPredictionRuntimeReview({ triggered_by: 'prediction_page_runtime_review' });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Runtime review failed.');
    } finally {
      setRunningRuntimeReview(false);
    }
  };

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Prediction agent"
        title="Prediction"
        description="System probability + market implied probability + auditable edge scoring for paper/demo proposals only. No real-money and no real execution."
        actions={(
          <div style={{ display: 'flex', gap: '0.75rem' }}>
            <button type="button" className="secondary-button" onClick={() => navigate('/proposals')}>Open Proposals</button>
            <button type="button" className="secondary-button" onClick={() => navigate('/agents')}>Open Agents</button>
            <button type="button" className="secondary-button" onClick={() => navigate('/risk-agent')}>Open Risk Agent</button>
            <button type="button" className="secondary-button" onClick={() => navigate('/champion-challenger')}>Open Champion Challenger</button>
          </div>
        )}
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

        <SectionCard
          eyebrow="Runtime hardening"
          title="Prediction runtime review / edge confidence board"
          description="Local-first/manual-first runtime layer. Combines active model (when available), heuristic fallback, narrative context, and precedent caution to emit auditable recommendations."
        >
          <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '0.75rem', flexWrap: 'wrap' }}>
            <button type="button" className="secondary-button" disabled={runningRuntimeReview} onClick={() => void runRuntimeReview()}>
              {runningRuntimeReview ? 'Running runtime review...' : 'Run prediction runtime review'}
            </button>
            <select value={runtimeStatusFilter} onChange={(e) => setRuntimeStatusFilter(e.target.value)}>
              <option value="">All statuses</option>
              <option value="STRONG_EDGE">STRONG_EDGE</option>
              <option value="WEAK_EDGE">WEAK_EDGE</option>
              <option value="LOW_CONFIDENCE">LOW_CONFIDENCE</option>
              <option value="NO_EDGE">NO_EDGE</option>
              <option value="CONFLICTED">CONFLICTED</option>
              <option value="NEEDS_REVIEW">NEEDS_REVIEW</option>
            </select>
          </div>
          <div className="system-metadata-grid">
            <div><strong>Candidates seen:</strong> {runtimeSummary?.latest_run?.candidate_count ?? 0}</div>
            <div><strong>Scored:</strong> {runtimeSummary?.latest_run?.scored_count ?? 0}</div>
            <div><strong>Strong edge:</strong> {runtimeSummary?.latest_run?.high_edge_count ?? 0}</div>
            <div><strong>Low confidence:</strong> {runtimeSummary?.latest_run?.low_confidence_count ?? 0}</div>
            <div><strong>Sent to risk:</strong> {runtimeSummary?.latest_run?.sent_to_risk_count ?? 0}</div>
            <div><strong>Sent to signal fusion:</strong> {runtimeSummary?.latest_run?.sent_to_signal_fusion_count ?? 0}</div>
          </div>
          {!runtimeSummary?.latest_run ? (
            <p style={{ marginTop: '0.75rem' }}>No prediction runtime assessments are available yet. Run a runtime review to score shortlisted markets.</p>
          ) : null}
        </SectionCard>



        <SectionCard
          eyebrow="Prediction intake"
          title="Prediction Intake & Conviction Review"
          description="Research→prediction→risk bridge hardening. Paper-only calibrated runtime review with uncertainty-aware confidence controls; no live execution."
        >
          <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '0.75rem', flexWrap: 'wrap' }}>
            <button type="button" className="secondary-button" disabled={runningIntakeReview} onClick={() => void runIntakeReview()}>
              {runningIntakeReview ? 'Running intake review...' : 'Run intake review'}
            </button>
          </div>
          <div className="system-metadata-grid">
            <div><strong>Handoffs considered:</strong> {intakeSummary?.latest_run?.considered_handoff_count ?? 0}</div>
            <div><strong>Runtime-ready:</strong> {intakeSummary?.latest_run?.runtime_candidate_count ?? 0}</div>
            <div><strong>Risk-ready:</strong> {intakeSummary?.latest_run?.risk_ready_count ?? 0}</div>
            <div><strong>Monitoring only:</strong> {intakeSummary?.latest_run?.monitoring_only_count ?? 0}</div>
            <div><strong>Ignored no-edge:</strong> {intakeSummary?.latest_run?.ignored_no_edge_count ?? 0}</div>
            <div><strong>Ignored low-confidence:</strong> {intakeSummary?.latest_run?.ignored_low_confidence_count ?? 0}</div>
            <div><strong>Manual review:</strong> {intakeSummary?.latest_run?.manual_review_count ?? 0}</div>
          </div>
        </SectionCard>

        <SectionCard eyebrow="Active model governance" title="Active model recommendation" description="Auditable recommendation only. Runtime model does not switch automatically.">
          <div className="system-metadata-grid">
            <div><strong>Active model:</strong> {governanceSummary?.active_model ? `${governanceSummary.active_model.name} (${governanceSummary.active_model.version})` : 'Heuristic fallback remains active.'}</div>
            <div><strong>Recommendation:</strong> <StatusBadge tone={recommendation?.recommendation_code === 'ACTIVATE_CANDIDATE' ? 'ready' : recommendation?.recommendation_code?.startsWith('KEEP') ? 'pending' : 'neutral'}>{recommendation?.recommendation_code ?? 'CAUTION_REVIEW_MANUALLY'}</StatusBadge></div>
            <div><strong>Latest winner:</strong> {recommendation?.winner ?? 'INCONCLUSIVE'}</div>
            <div><strong>Reasons:</strong> {(recommendation?.recommendation_reasons ?? []).join(', ') || 'No comparison run yet.'}</div>
          </div>
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

        <SectionCard eyebrow="Model comparison" title="Heuristic vs XGBoost comparison" description="Compare baseline predictor vs candidate by profile + scope to decide activation with evidence.">
          <div style={{ display: 'grid', gap: '0.75rem', gridTemplateColumns: '1fr 1fr 1fr 1fr auto' }}>
            <select value={comparisonBaselineKey} onChange={(e) => setComparisonBaselineKey(e.target.value)}>
              <option value="heuristic_baseline">heuristic_baseline</option>
              <option value="narrative_weighted">narrative_weighted</option>
              <option value="market_momentum_weighted">market_momentum_weighted</option>
              <option value="active_model">active_model</option>
            </select>
            <select value={comparisonCandidateKey} onChange={(e) => setComparisonCandidateKey(e.target.value)}>
              <option value="active_model">active_model</option>
              <option value="heuristic_baseline">heuristic_baseline</option>
              <option value="narrative_weighted">narrative_weighted</option>
              <option value="market_momentum_weighted">market_momentum_weighted</option>
              {models.map((model) => <option key={model.id} value={`artifact:${model.id}`}>artifact:{model.id} {model.name}:{model.version}</option>)}
            </select>
            <select value={comparisonProfileSlug} onChange={(e) => setComparisonProfileSlug(e.target.value)}>
              {modelProfiles.map((profile) => <option key={profile.id} value={profile.slug}>{profile.slug}</option>)}
            </select>
            <select value={comparisonScope} onChange={(e) => setComparisonScope(e.target.value as 'demo_only' | 'real_only' | 'mixed')}>
              <option value="mixed">mixed</option>
              <option value="demo_only">demo_only</option>
              <option value="real_only">real_only</option>
            </select>
            <button type="button" className="secondary-button" onClick={() => void runCompareModels()} disabled={comparingModels}>
              {comparingModels ? 'Comparing...' : 'Compare models'}
            </button>
          </div>
          {!models.length ? (
            <p style={{ marginTop: '0.75rem' }}>Train and activate a candidate model first.</p>
          ) : null}
        </SectionCard>

        <SectionCard eyebrow="Recent comparisons" title="Recent model comparison runs" description="Metrics side-by-side, winner badge, recommendation and rationale for activation governance.">
          {comparisonRuns.length === 0 ? (
            <EmptyState eyebrow="No comparisons" title="No model comparisons yet." description="Run Compare models to generate auditable governance evidence." />
          ) : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>ID</th><th>Status</th><th>Scope</th><th>Compared</th><th>Winner</th><th>Recommendation</th><th>Created</th></tr></thead>
                <tbody>
                  {comparisonRuns.map((run) => (
                    <tr key={run.id}>
                      <td>{run.id}</td>
                      <td>{run.status}</td>
                      <td>{run.scope}</td>
                      <td>{run.baseline_key} vs {run.candidate_key}</td>
                      <td><StatusBadge tone={run.winner === 'CANDIDATE_BETTER' ? 'ready' : run.winner === 'BASELINE_BETTER' ? 'offline' : 'neutral'}>{run.winner}</StatusBadge></td>
                      <td><StatusBadge tone={run.recommendation_code === 'ACTIVATE_CANDIDATE' ? 'ready' : run.recommendation_code.startsWith('KEEP') ? 'pending' : 'neutral'}>{run.recommendation_code}</StatusBadge></td>
                      <td>{new Date(run.created_at).toLocaleString()}</td>
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
                <thead><tr><th>Market</th><th>Profile</th><th>Edge</th><th>Confidence</th><th>Precedent context</th><th>Created</th></tr></thead>
                <tbody>
                  {recentScores.map((score) => (
                    <tr key={score.id}>
                      {(() => {
                        const precedent = (score.details?.precedent_context ?? {}) as Record<string, unknown>;
                        return (
                          <>
                      <td><button type="button" className="link-button" onClick={() => navigate(`/markets/${score.market_slug}`)}>{score.market_title}</button></td>
                      <td>{score.profile_slug}</td>
                      <td><StatusBadge tone={edgeTone(score.edge_label)}>{fmtPct(score.edge)}</StatusBadge></td>
                      <td><StatusBadge tone={confidenceTone(score.confidence_level)}>{fmtPct(score.confidence)}</StatusBadge></td>
                      <td>
                        {precedent.precedent_aware ? (
                          <div style={{ display: 'grid', gap: '0.25rem' }}>
                            <StatusBadge tone="pending">CAUTION_FROM_HISTORY</StatusBadge>
                            <small>{String(precedent.influence_mode ?? 'context_only')}</small>
                          </div>
                        ) : '—'}
                      </td>
                      <td>{new Date(score.created_at).toLocaleString()}</td>
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


        <SectionCard eyebrow="Intake candidates" title="Prediction intake candidates" description="Candidates consumed from research handoff with context and intake disposition.">
          <div className="table-wrapper"><table className="data-table"><thead><tr><th>Market</th><th>Handoff confidence</th><th>Narrative priority</th><th>Structural priority</th><th>Status</th><th>Summary</th></tr></thead><tbody>{intakeCandidates.map((item) => <tr key={item.id}><td>{item.market_title}</td><td>{fmtPct(item.handoff_confidence)}</td><td>{fmtPct(item.narrative_priority)}</td><td>{fmtPct(item.structural_priority)}</td><td><StatusBadge tone={item.intake_status === 'READY_FOR_RUNTIME' ? 'ready' : item.intake_status === 'BLOCKED' ? 'offline' : 'pending'}>{item.intake_status}</StatusBadge></td><td>{item.context_summary || '—'}</td></tr>)}</tbody></table></div>
        </SectionCard>

        <SectionCard eyebrow="Conviction reviews" title="Calibrated conviction reviews" description="Calibrated probability, adjusted edge, confidence and uncertainty for risk readiness.">
          <div className="table-wrapper"><table className="data-table"><thead><tr><th>Market</th><th>System</th><th>Market</th><th>Calibrated</th><th>Adjusted edge</th><th>Confidence</th><th>Uncertainty</th><th>Bucket</th><th>Status</th></tr></thead><tbody>{convictionReviews.map((item) => <tr key={item.id}><td>{item.intake_candidate.market_title}</td><td>{fmtPct(item.system_probability)}</td><td>{fmtPct(item.market_probability)}</td><td>{fmtPct(item.calibrated_probability)}</td><td>{fmtPct(item.adjusted_edge)}</td><td>{fmtPct(item.confidence)}</td><td>{fmtPct(item.uncertainty)}</td><td>{item.conviction_bucket}</td><td>{item.review_status}</td></tr>)}</tbody></table></div>
        </SectionCard>

        <SectionCard eyebrow="Risk handoffs" title="Risk-ready prediction handoffs" description="Explicit prediction→risk handoff status and rationale.">
          <div className="table-wrapper"><table className="data-table"><thead><tr><th>Market</th><th>Status</th><th>Confidence</th><th>Reason codes</th><th>Summary</th></tr></thead><tbody>{riskHandoffs.map((item) => <tr key={item.id}><td>{item.market_title}</td><td>{item.handoff_status}</td><td>{fmtPct(item.handoff_confidence)}</td><td>{item.handoff_reason_codes.join(', ') || '—'}</td><td>{item.handoff_summary}</td></tr>)}</tbody></table></div>
        </SectionCard>

        <SectionCard eyebrow="Intake recommendations" title="Prediction intake recommendations" description="Conservative recommendation layer for prediction→risk routing decisions.">
          <div className="table-wrapper"><table className="data-table"><thead><tr><th>Type</th><th>Rationale</th><th>Blockers</th><th>Confidence</th></tr></thead><tbody>{intakeRecommendations.map((item) => <tr key={item.id}><td>{item.recommendation_type}</td><td>{item.rationale}</td><td>{item.blockers.join(', ') || '—'}</td><td>{fmtPct(item.confidence)}</td></tr>)}</tbody></table></div>
        </SectionCard>

        <SectionCard eyebrow="Runtime assessments" title="Calibrated probability + adjusted edge board" description="Assessment-level runtime outputs for prediction→risk/signal handoff.">
          {runtimeAssessments.length === 0 ? (
            <EmptyState eyebrow="No runtime assessments" title="No prediction runtime assessments are available yet." description="Run a runtime review to score shortlisted markets." />
          ) : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Market</th><th>Provider/Category</th><th>Market</th><th>Calibrated</th><th>Adjusted edge</th><th>Confidence</th><th>Uncertainty</th><th>Evidence</th><th>Precedent caution</th><th>Status</th><th>Links</th></tr></thead>
                <tbody>
                  {runtimeAssessments.map((item) => (
                    <tr key={item.id}>
                      <td>{item.candidate.market_title}</td>
                      <td>{item.candidate.market_provider} / {item.candidate.category || '—'}</td>
                      <td>{fmtPct(item.market_probability)}</td>
                      <td>{fmtPct(item.calibrated_probability)}</td>
                      <td>{fmtPct(item.adjusted_edge)}</td>
                      <td>{fmtPct(item.confidence_score)}</td>
                      <td>{fmtPct(item.uncertainty_score)}</td>
                      <td>{fmtPct(item.evidence_quality_score)}</td>
                      <td>{fmtPct(item.precedent_caution_score)}</td>
                      <td><StatusBadge tone={item.prediction_status === 'STRONG_EDGE' ? 'ready' : item.prediction_status === 'LOW_CONFIDENCE' ? 'pending' : item.prediction_status === 'CONFLICTED' ? 'offline' : 'neutral'}>{item.prediction_status}</StatusBadge></td>
                      <td><button className="link-button" type="button" onClick={() => navigate(`/markets/${item.candidate.market_slug}`)}>Market</button>{' · '}<button className="link-button" type="button" onClick={() => navigate('/research-agent')}>Research</button>{' · '}<button className="link-button" type="button" onClick={() => navigate('/risk-agent')}>Risk</button>{' · '}<button className="link-button" type="button" onClick={() => navigate('/trace')}>Trace</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Runtime recommendations" title="Prediction runtime recommendations" description="Recommendation-first handoff. Prediction does not authorize execution nor bypass risk/policy/safety.">
          {runtimeRecommendations.length === 0 ? (
            <EmptyState eyebrow="No recommendations" title="Runtime recommendations appear after running runtime review." description="LOW_CONFIDENCE and NO_EDGE are valid outcomes, not bugs." />
          ) : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Recommendation</th><th>Rationale</th><th>Reason codes</th><th>Confidence</th></tr></thead>
                <tbody>
                  {runtimeRecommendations.map((item) => (
                    <tr key={item.id}>
                      <td><StatusBadge tone={item.recommendation_type === 'SEND_TO_RISK_ASSESSMENT' ? 'ready' : item.recommendation_type === 'IGNORE_LOW_CONFIDENCE' ? 'pending' : 'neutral'}>{item.recommendation_type}</StatusBadge></td>
                      <td>{item.rationale}</td>
                      <td>{item.reason_codes.join(', ') || '—'}</td>
                      <td>{fmtPct(item.confidence)}</td>
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

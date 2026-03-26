import { requestJson } from './api/client';
import type {
  ActiveModelRecommendation,
  ModelComparisonRun,
  ModelEvaluationProfile,
  ModelGovernanceSummary,
  PredictionModelArtifact,
  PredictionProfile,
  PredictionScore,
  PredictionSummary,
  PredictionTrainingRun,
  PredictionTrainingSummary,
  ScoreMarketPayload,
} from '../types/prediction';

export function getPredictionProfiles() {
  return requestJson<PredictionProfile[]>('/api/prediction/profiles/');
}

export function scoreMarketPrediction(payload: ScoreMarketPayload) {
  return requestJson<PredictionScore>('/api/prediction/score-market/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getPredictionScores() {
  return requestJson<PredictionScore[]>('/api/prediction/scores/');
}

export function getPredictionSummary() {
  return requestJson<PredictionSummary>('/api/prediction/summary/');
}

export function getPredictionTrainingSummary() {
  return requestJson<PredictionTrainingSummary>('/api/prediction/train/summary/');
}

export function getPredictionTrainingRuns() {
  return requestJson<PredictionTrainingRun[]>('/api/prediction/train/runs/');
}

export function getPredictionModels() {
  return requestJson<PredictionModelArtifact[]>('/api/prediction/models/');
}

export function buildPredictionDataset(payload?: { name?: string; horizon_hours?: number }) {
  return requestJson('/api/prediction/train/build-dataset/', {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function trainPredictionModel(payload: { dataset_run_id: number; model_name?: string }) {
  return requestJson('/api/prediction/train/run/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function activatePredictionModel(id: number) {
  return requestJson(`/api/prediction/models/${id}/activate/`, {
    method: 'POST',
    body: JSON.stringify({}),
  });
}

export function getModelProfiles() {
  return requestJson<ModelEvaluationProfile[]>('/api/prediction/model-profiles/');
}

export function compareModels(payload: {
  baseline_key: string;
  candidate_key: string;
  profile_slug: string;
  scope: 'demo_only' | 'real_only' | 'mixed';
  dataset_run_id?: number;
}) {
  return requestJson<ModelComparisonRun>('/api/prediction/compare-models/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getModelComparisons() {
  return requestJson<ModelComparisonRun[]>('/api/prediction/comparisons/');
}

export function getActiveModelRecommendation() {
  return requestJson<ActiveModelRecommendation>('/api/prediction/active-model-recommendation/');
}

export function getModelGovernanceSummary() {
  return requestJson<ModelGovernanceSummary>('/api/prediction/model-governance-summary/');
}

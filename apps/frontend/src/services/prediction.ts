import { requestJson } from './api/client';
import type { PredictionProfile, PredictionScore, PredictionSummary, ScoreMarketPayload } from '../types/prediction';

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

export function getPredictionScore(id: number | string) {
  return requestJson<PredictionScore>(`/api/prediction/scores/${id}/`);
}

export function getPredictionSummary() {
  return requestJson<PredictionSummary>('/api/prediction/summary/');
}

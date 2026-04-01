import { requestJson } from './api/client';
import type {
  MarketResearchCandidate,
  MarketResearchRecommendation,
  MarketTriageDecision,
  PredictionHandoffCandidate,
  ResearchPursuitRecommendation,
  ResearchPursuitScore,
  ResearchPursuitSummary,
  ResearchStructuralAssessment,
  ResearchUniverseSummary,
} from '../types/researchAgent';

export function runResearchUniverseScan(payload: { provider_scope?: string[]; source_scope?: string[] } = {}) {
  return requestJson('/api/research-agent/run-universe-scan/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function runPursuitReview(payload: { market_limit?: number } = {}) {
  return requestJson('/api/research-agent/run-pursuit-review/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getResearchCandidates() {
  return requestJson<MarketResearchCandidate[]>('/api/research-agent/candidates/');
}

export function getResearchTriageDecisions() {
  return requestJson<MarketTriageDecision[]>('/api/research-agent/triage-decisions/');
}

export function getResearchRecommendations() {
  return requestJson<MarketResearchRecommendation[]>('/api/research-agent/recommendations/');
}

export function getResearchUniverseSummary() {
  return requestJson<ResearchUniverseSummary>('/api/research-agent/universe-summary/');
}

export function getPursuitSummary() {
  return requestJson<ResearchPursuitSummary>('/api/research-agent/pursuit-summary/');
}

export function getStructuralAssessments() {
  return requestJson<ResearchStructuralAssessment[]>('/api/research-agent/structural-assessments/');
}

export function getPursuitScores() {
  return requestJson<ResearchPursuitScore[]>('/api/research-agent/pursuit-scores/');
}

export function getPredictionHandoffs() {
  return requestJson<PredictionHandoffCandidate[]>('/api/research-agent/prediction-handoffs/');
}

export function getPursuitRecommendations() {
  return requestJson<ResearchPursuitRecommendation[]>('/api/research-agent/pursuit-recommendations/');
}

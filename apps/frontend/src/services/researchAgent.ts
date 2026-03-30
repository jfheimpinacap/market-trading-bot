import { requestJson } from './api/client';
import type {
  MarketResearchCandidate,
  MarketResearchRecommendation,
  MarketTriageDecision,
  ResearchUniverseSummary,
} from '../types/researchAgent';

export function runResearchUniverseScan(payload: { provider_scope?: string[]; source_scope?: string[] } = {}) {
  return requestJson('/api/research-agent/run-universe-scan/', {
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

import { requestJson } from './api/client';
import type {
  AutonomyInsightCandidate,
  AutonomyInsightSummary,
  CampaignInsight,
  InsightRecommendation,
  RunAutonomyInsightReviewResponse,
} from '../types/autonomyInsights';

export function getAutonomyInsightCandidates() {
  return requestJson<AutonomyInsightCandidate[]>('/api/autonomy-insights/candidates/');
}

export function runAutonomyInsightsReview(payload?: { actor?: string }) {
  return requestJson<RunAutonomyInsightReviewResponse>('/api/autonomy-insights/run-review/', {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function getAutonomyInsights() {
  return requestJson<CampaignInsight[]>('/api/autonomy-insights/insights/');
}

export function getAutonomyInsightRecommendations() {
  return requestJson<InsightRecommendation[]>('/api/autonomy-insights/recommendations/');
}

export function getAutonomyInsightSummary() {
  return requestJson<AutonomyInsightSummary>('/api/autonomy-insights/summary/');
}

export function markAutonomyInsightReviewed(insightId: number, payload?: { actor?: string }) {
  return requestJson<{ insight_id: number; reviewed: boolean }>(`/api/autonomy-insights/mark-reviewed/${insightId}/`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

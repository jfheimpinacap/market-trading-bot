import { requestJson } from './api/client';
import type {
  BaselineResponseCase,
  BaselineResponseRecommendationItem,
  BaselineResponseSummary,
  ResponseEvidencePack,
  ResponseRoutingDecision,
} from '../types/certification';

export type RunBaselineResponseReviewInput = {
  actor?: string;
  metadata?: Record<string, unknown>;
};

export function runBaselineResponseReview(input: RunBaselineResponseReviewInput = {}) {
  return requestJson<{
    run: Record<string, unknown>;
    case_count: number;
    evidence_pack_count: number;
    routing_decision_count: number;
    recommendation_count: number;
  }>('/api/certification/run-baseline-response-review/', {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export function getBaselineResponseCases() {
  return requestJson<BaselineResponseCase[]>('/api/certification/response-cases/');
}

export function getBaselineResponseEvidencePacks() {
  return requestJson<ResponseEvidencePack[]>('/api/certification/response-evidence-packs/');
}

export function getBaselineResponseRoutingDecisions() {
  return requestJson<ResponseRoutingDecision[]>('/api/certification/response-routing-decisions/');
}

export function getBaselineResponseRecommendations() {
  return requestJson<BaselineResponseRecommendationItem[]>('/api/certification/response-recommendations/');
}

export function getBaselineResponseSummary() {
  return requestJson<BaselineResponseSummary>('/api/certification/response-summary/');
}

import { requestJson } from './api/client';
import type {
  BaselineResponseResolutionSummary,
  DownstreamOutcomeReference,
  ResponseCaseResolution,
  ResponseResolutionCandidate,
  ResponseResolutionRecommendationItem,
} from '../types/certification';

export function runBaselineResponseResolution(input: { actor?: string; metadata?: Record<string, unknown> } = {}) {
  return requestJson('/api/certification/run-baseline-response-resolution/', {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export function getBaselineResponseResolutionCandidates() {
  return requestJson<ResponseResolutionCandidate[]>('/api/certification/response-resolution-candidates/');
}

export function getBaselineResponseCaseResolutions() {
  return requestJson<ResponseCaseResolution[]>('/api/certification/response-case-resolutions/');
}

export function getDownstreamOutcomeReferences() {
  return requestJson<DownstreamOutcomeReference[]>('/api/certification/downstream-outcome-references/');
}

export function getBaselineResponseResolutionRecommendations() {
  return requestJson<ResponseResolutionRecommendationItem[]>('/api/certification/response-resolution-recommendations/');
}

export function getBaselineResponseResolutionSummary() {
  return requestJson<BaselineResponseResolutionSummary>('/api/certification/response-resolution-summary/');
}

export function resolveBaselineResponseCase(caseId: number, input: Record<string, unknown>) {
  return requestJson(`/api/certification/resolve-response-case/${caseId}/`, {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

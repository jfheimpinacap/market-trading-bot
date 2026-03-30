import { requestJson } from './api/client';
import type {
  CertificationCandidate,
  CertificationDecision,
  CertificationEvidencePack,
  CertificationRecommendationItem,
  PostRolloutCertificationSummary,
  RolloutCertificationRun,
} from '../types/certification';

export function runPostRolloutCertificationReview(payload: Record<string, unknown> = {}) {
  return requestJson<{
    run: RolloutCertificationRun;
    candidate_count: number;
    evidence_pack_count: number;
    decision_count: number;
    recommendation_count: number;
  }>('/api/certification/run-post-rollout-review/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getCertificationCandidates() {
  return requestJson<CertificationCandidate[]>('/api/certification/candidates/');
}

export function getCertificationEvidencePacks() {
  return requestJson<CertificationEvidencePack[]>('/api/certification/evidence-packs/');
}

export function getCertificationDecisions() {
  return requestJson<CertificationDecision[]>('/api/certification/decisions/');
}

export function getCertificationRecommendations() {
  return requestJson<CertificationRecommendationItem[]>('/api/certification/recommendations/');
}

export function getCertificationSummary() {
  return requestJson<PostRolloutCertificationSummary>('/api/certification/post-rollout-summary/');
}

import { requestJson } from './api/client';
import type { CertificationRun, CertificationSummary } from '../types/certification';

export function runCertificationReview(payload: Record<string, unknown> = {}) {
  return requestJson<CertificationRun>('/api/certification/run-review/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getCertificationRuns() {
  return requestJson<CertificationRun[]>('/api/certification/runs/');
}

export function getCertificationRun(id: number) {
  return requestJson<CertificationRun>(`/api/certification/runs/${id}/`);
}

export function getCurrentCertification() {
  return requestJson<{ current_certification: CertificationRun | null }>('/api/certification/current/');
}

export function getCertificationSummary() {
  return requestJson<CertificationSummary>('/api/certification/summary/');
}

export function applyCertificationDecision(id: number, payload: Record<string, unknown> = {}) {
  return requestJson<CertificationRun>(`/api/certification/apply/${id}/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

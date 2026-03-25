import { requestJson } from './api/client';
import type {
  ReadinessAssessmentRun,
  ReadinessProfile,
  ReadinessSummary,
  RunReadinessAssessmentPayload,
} from '../types/readiness';

export function getReadinessProfiles() {
  return requestJson<ReadinessProfile[]>('/api/readiness/profiles/');
}

export function getReadinessProfile(id: string | number) {
  return requestJson<ReadinessProfile>(`/api/readiness/profiles/${id}/`);
}

export function runReadinessAssessment(payload: RunReadinessAssessmentPayload) {
  return requestJson<ReadinessAssessmentRun>('/api/readiness/assess/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getReadinessRuns() {
  return requestJson<ReadinessAssessmentRun[]>('/api/readiness/runs/');
}

export function getReadinessRun(id: string | number) {
  return requestJson<ReadinessAssessmentRun>(`/api/readiness/runs/${id}/`);
}

export function getReadinessSummary() {
  return requestJson<ReadinessSummary>('/api/readiness/summary/');
}

export function seedReadinessProfiles() {
  return requestJson<{ created: number; updated: number; total: number }>('/api/readiness/seed-profiles/', {
    method: 'POST',
    body: JSON.stringify({}),
  });
}

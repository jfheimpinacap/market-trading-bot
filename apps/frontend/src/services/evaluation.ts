import { requestJson } from './api/client';
import type { EvaluationComparison, EvaluationRun, EvaluationSummary } from '../types/evaluation';

export function getEvaluationSummary() {
  return requestJson<EvaluationSummary>('/api/evaluation/summary/');
}

export function getEvaluationRuns() {
  return requestJson<EvaluationRun[]>('/api/evaluation/runs/');
}

export function getEvaluationRun(id: string | number) {
  return requestJson<EvaluationRun>(`/api/evaluation/runs/${id}/`);
}

export function buildEvaluationForSession(sessionId: string | number) {
  return requestJson<EvaluationRun>(`/api/evaluation/build-for-session/${sessionId}/`, {
    method: 'POST',
    body: JSON.stringify({}),
  });
}

export function getEvaluationRecent() {
  return requestJson<EvaluationRun[]>('/api/evaluation/recent/');
}

export function getEvaluationComparison(leftId: string | number, rightId: string | number) {
  return requestJson<EvaluationComparison>(`/api/evaluation/comparison/?left_id=${leftId}&right_id=${rightId}`);
}

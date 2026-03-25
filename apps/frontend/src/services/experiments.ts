import { requestJson } from './api/client';
import type { ExperimentComparison, ExperimentRun, ExperimentSummary, RunExperimentPayload, StrategyProfile } from '../types/experiments';

export function getStrategyProfiles() {
  return requestJson<StrategyProfile[]>('/api/experiments/profiles/');
}

export function getStrategyProfile(id: string | number) {
  return requestJson<StrategyProfile>(`/api/experiments/profiles/${id}/`);
}

export function runExperiment(payload: RunExperimentPayload) {
  return requestJson<ExperimentRun>('/api/experiments/run/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getExperimentRuns() {
  return requestJson<ExperimentRun[]>('/api/experiments/runs/');
}

export function getExperimentRun(id: string | number) {
  return requestJson<ExperimentRun>(`/api/experiments/runs/${id}/`);
}

export function getExperimentComparison(leftRunId: string | number, rightRunId: string | number) {
  return requestJson<ExperimentComparison>(`/api/experiments/comparison/?left_run_id=${leftRunId}&right_run_id=${rightRunId}`);
}

export function getExperimentSummary() {
  return requestJson<ExperimentSummary>('/api/experiments/summary/');
}

export function seedExperimentProfiles() {
  return requestJson<{ created: number; updated: number; total: number }>('/api/experiments/seed-profiles/', {
    method: 'POST',
    body: JSON.stringify({}),
  });
}

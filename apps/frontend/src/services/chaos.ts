import { requestJson } from './api/client';
import type { ChaosExperiment, ChaosRun, ChaosSummary, ResilienceBenchmark, RunChaosExperimentPayload } from '../types/chaos';

export function getChaosExperiments() {
  return requestJson<ChaosExperiment[]>('/api/chaos/experiments/');
}

export function runChaosExperiment(payload: RunChaosExperimentPayload) {
  return requestJson<ChaosRun>('/api/chaos/run/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getChaosRuns() {
  return requestJson<ChaosRun[]>('/api/chaos/runs/');
}

export function getChaosRun(id: number) {
  return requestJson<ChaosRun>(`/api/chaos/runs/${id}/`);
}

export function getChaosBenchmarks() {
  return requestJson<ResilienceBenchmark[]>('/api/chaos/benchmarks/');
}

export function getChaosSummary() {
  return requestJson<ChaosSummary>('/api/chaos/summary/');
}

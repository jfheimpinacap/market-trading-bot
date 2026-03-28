import { requestJson } from './api/client';
import type { AutonomyScenarioRun, AutonomyScenarioSummary, ScenarioRecommendation } from '../types/autonomyScenario';

export function runAutonomyScenario(payload?: { requested_by?: string; notes?: string }) {
  return requestJson<AutonomyScenarioRun>('/api/autonomy-scenario/run/', {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function getAutonomyScenarioRuns() {
  return requestJson<AutonomyScenarioRun[]>('/api/autonomy-scenario/runs/');
}

export function getAutonomyScenarioRun(id: number) {
  return requestJson<AutonomyScenarioRun>(`/api/autonomy-scenario/runs/${id}/`);
}

export function getAutonomyScenarioOptions() {
  return requestJson<{ options: Array<Record<string, unknown>> }>('/api/autonomy-scenario/options/');
}

export function getAutonomyScenarioRecommendations() {
  return requestJson<ScenarioRecommendation[]>('/api/autonomy-scenario/recommendations/');
}

export function getAutonomyScenarioSummary() {
  return requestJson<AutonomyScenarioSummary>('/api/autonomy-scenario/summary/');
}

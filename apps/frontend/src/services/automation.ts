import { requestJson } from './api/client';
import type { DemoAutomationRun, DemoAutomationSummary, DemoAutomationTriggeredFrom } from '../types/automation';

function buildQueryString(limit?: number) {
  if (!limit) {
    return '';
  }

  const searchParams = new URLSearchParams();
  searchParams.set('limit', String(limit));
  return `?${searchParams.toString()}`;
}

function postAutomationAction(path: string, triggered_from: DemoAutomationTriggeredFrom = 'automation_page') {
  return requestJson<DemoAutomationRun>(path, {
    method: 'POST',
    body: JSON.stringify({ triggered_from }),
  });
}

export function runSimulationTick(triggeredFrom?: DemoAutomationTriggeredFrom) {
  return postAutomationAction('/api/automation/simulate-tick/', triggeredFrom);
}

export function runGenerateSignals(triggeredFrom?: DemoAutomationTriggeredFrom) {
  return postAutomationAction('/api/automation/generate-signals/', triggeredFrom);
}

export function runRevaluePortfolio(triggeredFrom?: DemoAutomationTriggeredFrom) {
  return postAutomationAction('/api/automation/revalue-portfolio/', triggeredFrom);
}

export function runGenerateTradeReviews(triggeredFrom?: DemoAutomationTriggeredFrom) {
  return postAutomationAction('/api/automation/generate-trade-reviews/', triggeredFrom);
}

export function runSyncDemoState(triggeredFrom?: DemoAutomationTriggeredFrom) {
  return postAutomationAction('/api/automation/sync-demo-state/', triggeredFrom);
}

export function runDemoCycle(triggeredFrom?: DemoAutomationTriggeredFrom) {
  return postAutomationAction('/api/automation/run-demo-cycle/', triggeredFrom);
}

export function runRebuildLearningMemory(triggeredFrom?: DemoAutomationTriggeredFrom) {
  return postAutomationAction('/api/automation/rebuild-learning-memory/', triggeredFrom);
}

export function runFullLearningCycle(triggeredFrom?: DemoAutomationTriggeredFrom) {
  return postAutomationAction('/api/automation/run-full-learning-cycle/', triggeredFrom);
}

export function getAutomationRuns(limit?: number) {
  return requestJson<DemoAutomationRun[]>(`/api/automation/runs/${buildQueryString(limit)}`);
}

export function getAutomationRun(id: string | number) {
  return requestJson<DemoAutomationRun>(`/api/automation/runs/${id}/`);
}

export function getAutomationSummary() {
  return requestJson<DemoAutomationSummary>('/api/automation/summary/');
}

import { requestJson } from './api/client';
import type {
  AutonomousTradeCandidate,
  AutonomousTradeDecision,
  AutonomousTradeExecution,
  AutonomousTradeOutcome,
  AutonomousTradeWatchRecord,
  AutonomousTraderSummary,
} from '../types/autonomousTrader';

export function runAutonomousTraderCycle() {
  return requestJson<{ run: number; candidate_count: number }>('/api/autonomous-trader/run-cycle/', {
    method: 'POST',
    body: JSON.stringify({}),
  });
}

export function runAutonomousTraderWatchCycle() {
  return requestJson<{ run: number; watch_records: number }>('/api/autonomous-trader/run-watch-cycle/', {
    method: 'POST',
    body: JSON.stringify({}),
  });
}

export const getAutonomousTraderSummary = () => requestJson<AutonomousTraderSummary>('/api/autonomous-trader/summary/');
export const getAutonomousTraderCandidates = () => requestJson<AutonomousTradeCandidate[]>('/api/autonomous-trader/candidates/');
export const getAutonomousTraderDecisions = () => requestJson<AutonomousTradeDecision[]>('/api/autonomous-trader/decisions/');
export const getAutonomousTraderExecutions = () => requestJson<AutonomousTradeExecution[]>('/api/autonomous-trader/executions/');
export const getAutonomousTraderWatchRecords = () => requestJson<AutonomousTradeWatchRecord[]>('/api/autonomous-trader/watch-records/');
export const getAutonomousTraderOutcomes = () => requestJson<AutonomousTradeOutcome[]>('/api/autonomous-trader/outcomes/');

import { requestJson } from './api/client';
import type {
  AutonomousLearningHandoff,
  AutonomousOutcomeHandoffRecommendation,
  AutonomousOutcomeHandoffSummary,
  AutonomousPostmortemHandoff,
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

export function runAutonomousOutcomeHandoff() {
  return requestJson<{ run: number }>('/api/autonomous-trader/run-outcome-handoff/', {
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
export const getAutonomousOutcomeHandoffSummary = () => requestJson<AutonomousOutcomeHandoffSummary>('/api/autonomous-trader/outcome-handoff-summary/');
export const getAutonomousPostmortemHandoffs = () => requestJson<AutonomousPostmortemHandoff[]>('/api/autonomous-trader/postmortem-handoffs/');
export const getAutonomousLearningHandoffs = () => requestJson<AutonomousLearningHandoff[]>('/api/autonomous-trader/learning-handoffs/');
export const getAutonomousOutcomeHandoffRecommendations = () => requestJson<AutonomousOutcomeHandoffRecommendation[]>('/api/autonomous-trader/outcome-handoff-recommendations/');

import { requestJson } from './api/client';
import type { EvaluateTradePolicyPayload, PolicyDecisionSummary, TradePolicyEvaluation } from '../types/policy';

export function evaluateTradePolicy(payload: EvaluateTradePolicyPayload) {
  return requestJson<TradePolicyEvaluation>('/api/policy/evaluate-trade/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getPolicyDecisions(marketId?: number) {
  const query = marketId ? `?market=${marketId}` : '';
  return requestJson<TradePolicyEvaluation[]>(`/api/policy/decisions/${query}`);
}

export function getPolicySummary() {
  return requestJson<PolicyDecisionSummary>('/api/policy/summary/');
}

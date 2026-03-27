import { requestJson } from './api/client';
import type { PositionWatchEvent, PositionWatchRun, RiskAssessment, RiskSizingDecision, RiskSummary } from '../types/riskAgent';

export function runRiskAssessment(payload: { market_id?: number; proposal_id?: number; prediction_score_id?: number; metadata?: Record<string, unknown> }) {
  return requestJson<{ assessment: RiskAssessment }>('/api/risk-agent/assess/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function runRiskSizing(payload: { risk_assessment_id: number; base_quantity: string; metadata?: Record<string, unknown> }) {
  return requestJson<{ sizing: RiskSizingDecision }>('/api/risk-agent/size/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function runRiskWatch() {
  return requestJson<{ watch_run: PositionWatchRun }>('/api/risk-agent/run-watch/', {
    method: 'POST',
    body: JSON.stringify({}),
  });
}

export function getRiskAssessments() {
  return requestJson<RiskAssessment[]>('/api/risk-agent/assessments/');
}

export function getRiskWatchEvents() {
  return requestJson<PositionWatchEvent[]>('/api/risk-agent/watch-events/');
}

export function getRiskSummary() {
  return requestJson<RiskSummary>('/api/risk-agent/summary/');
}

export function runRiskPrecedentAssist(payload: { query_text: string; assessment_id?: number; limit?: number }) {
  return requestJson<{
    retrieval_run_id: number;
    result_count: number;
    influence_mode: string;
    precedent_confidence: number;
    summary: Record<string, unknown>;
  }>('/api/risk-agent/precedent-assist/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

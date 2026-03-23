import { requestJson } from './api/client';
import type { AssessTradePayload, AssessTradeResponse, TradeRiskAssessment } from '../types/riskDemo';

export function assessTrade(payload: AssessTradePayload) {
  return requestJson<AssessTradeResponse>('/api/risk/assess-trade/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getRiskAssessments(marketId?: number) {
  const query = marketId ? `?market=${marketId}` : '';
  return requestJson<TradeRiskAssessment[]>(`/api/risk/assessments/${query}`);
}

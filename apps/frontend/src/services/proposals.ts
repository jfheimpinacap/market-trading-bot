import { requestJson } from './api/client';
import type { GenerateTradeProposalPayload, GenerateTradeProposalResponse, TradeProposal, TradeProposalQueryParams } from '../types/proposals';

function buildQueryString(params?: TradeProposalQueryParams) {
  if (!params) {
    return '';
  }

  const searchParams = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null) {
      return;
    }

    const normalized = `${value}`.trim();
    if (!normalized) {
      return;
    }

    searchParams.set(key, normalized);
  });

  const queryString = searchParams.toString();
  return queryString ? `?${queryString}` : '';
}

export function getTradeProposals(params?: TradeProposalQueryParams) {
  return requestJson<TradeProposal[]>(`/api/proposals/${buildQueryString(params)}`);
}

export function getTradeProposal(id: number | string) {
  return requestJson<TradeProposal>(`/api/proposals/${id}/`);
}

export function generateTradeProposal(payload: GenerateTradeProposalPayload) {
  return requestJson<GenerateTradeProposalResponse>('/api/proposals/generate/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

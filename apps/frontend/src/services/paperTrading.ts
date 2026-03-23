import { requestJson } from './api/client';
import type {
  CreatePaperTradePayload,
  CreatePaperTradeResponse,
  PaperAccount,
  PaperPortfolioSnapshot,
  PaperPortfolioSummary,
  PaperPosition,
  PaperTrade,
} from '../types/paperTrading';

export function getPaperAccount() {
  return requestJson<PaperAccount>('/api/paper/account/');
}

export function getPaperPositions() {
  return requestJson<PaperPosition[]>('/api/paper/positions/');
}

export function getPaperTrades() {
  return requestJson<PaperTrade[]>('/api/paper/trades/');
}

export function createPaperTrade(payload: CreatePaperTradePayload) {
  return requestJson<CreatePaperTradeResponse>('/api/paper/trades/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getPaperSummary() {
  return requestJson<PaperPortfolioSummary>('/api/paper/summary/');
}

export function revaluePaperPortfolio() {
  return requestJson<PaperAccount>('/api/paper/revalue/', {
    method: 'POST',
  });
}

export function getPaperSnapshots() {
  return requestJson<PaperPortfolioSnapshot[]>('/api/paper/snapshots/');
}

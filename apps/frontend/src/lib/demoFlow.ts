import type { PaperPosition, PaperTrade } from '../types/paperTrading';
import type { TradeReview } from '../types/reviews';
import type { MarketSignal } from '../types/signals';

export const DEMO_FLOW_REFRESH_EVENT = 'demo-flow-refresh';
export const DEMO_FLOW_REFRESH_STORAGE_KEY = 'market-trading-bot.demo-flow-refresh';

function sortByNewest<T>(items: T[], getDate: (item: T) => string) {
  return [...items].sort((left, right) => new Date(getDate(right)).getTime() - new Date(getDate(left)).getTime());
}

export function publishDemoFlowRefresh(reason: string) {
  const detail = {
    reason,
    timestamp: new Date().toISOString(),
  };

  window.localStorage.setItem(DEMO_FLOW_REFRESH_STORAGE_KEY, JSON.stringify(detail));
  window.dispatchEvent(new CustomEvent(DEMO_FLOW_REFRESH_EVENT, { detail }));
}

export function getOpenPositionsForMarket(positions: PaperPosition[], marketId: number) {
  return positions.filter((position) => position.market === marketId && position.status === 'OPEN' && Number(position.quantity) > 0);
}

export function getLatestTradeForMarket(trades: PaperTrade[], marketId: number) {
  return sortByNewest(
    trades.filter((trade) => trade.market === marketId),
    (trade) => trade.executed_at,
  )[0] ?? null;
}

export function getLatestReviewForMarket(reviews: TradeReview[], marketId: number) {
  return sortByNewest(
    reviews.filter((review) => review.market === marketId),
    (review) => review.reviewed_at,
  )[0] ?? null;
}

export function getLatestReviewForTrade(reviews: TradeReview[], tradeId: number) {
  return sortByNewest(
    reviews.filter((review) => review.trade_id === tradeId),
    (review) => review.reviewed_at,
  )[0] ?? null;
}

export function buildReviewLookupByTradeId(reviews: TradeReview[]) {
  return Object.fromEntries(reviews.map((review) => [review.trade_id, review]));
}

export function getSignalsForMarket(signals: MarketSignal[], marketId: number) {
  return signals.filter((signal) => signal.market === marketId);
}

export function formatActionableLabel(isActionable: boolean) {
  return isActionable ? 'Actionable' : 'Not actionable';
}

export function formatDecisionLabel(value: string | null | undefined) {
  if (!value) {
    return 'Not evaluated';
  }

  return value
    .toLowerCase()
    .split(/[_\s]+/)
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(' ');
}

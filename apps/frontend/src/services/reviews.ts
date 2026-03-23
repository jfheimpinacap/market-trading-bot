import { requestJson } from './api/client';
import type { ReviewFilters, TradeReview, TradeReviewDetail, TradeReviewSummary } from '../types/reviews';

function buildQueryString(params?: ReviewFilters) {
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

export function getTradeReviews(params?: ReviewFilters) {
  return requestJson<TradeReview[]>(`/api/reviews/${buildQueryString(params)}`);
}

export function getTradeReview(id: string | number) {
  return requestJson<TradeReviewDetail>(`/api/reviews/${id}/`);
}

export function getReviewsSummary() {
  return requestJson<TradeReviewSummary>('/api/reviews/summary/');
}

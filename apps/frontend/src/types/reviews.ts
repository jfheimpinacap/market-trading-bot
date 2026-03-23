export type TradeReviewOutcome = 'FAVORABLE' | 'NEUTRAL' | 'UNFAVORABLE' | string;
export type TradeReviewStatus = 'PENDING' | 'REVIEWED' | 'STALE' | string;

export type TradeReview = {
  id: number;
  paper_trade: number;
  trade_id: number;
  trade_type: string;
  trade_side: string;
  trade_quantity: string;
  trade_executed_at: string;
  paper_account: number;
  paper_account_slug: string;
  paper_account_name: string;
  market: number;
  market_title: string;
  market_slug: string;
  market_status: string;
  review_status: TradeReviewStatus;
  outcome: TradeReviewOutcome;
  score: string;
  confidence: string;
  summary: string;
  lesson: string;
  recommendation: string;
  entry_price: string | null;
  current_market_price: string | null;
  price_delta: string | null;
  pnl_estimate: string | null;
  market_probability_at_trade: string | null;
  market_probability_now: string | null;
  risk_decision_at_trade: string;
  reviewed_at: string;
  created_at: string;
  updated_at: string;
};

export type TradeReviewDetail = TradeReview & {
  rationale: string;
  signals_context: Array<Record<string, unknown>>;
  trade_notes: string;
  trade_metadata: Record<string, unknown>;
  metadata: Record<string, unknown>;
};

export type TradeReviewSummary = {
  total_reviews: number;
  reviewed_reviews: number;
  stale_reviews: number;
  favorable_reviews: number;
  neutral_reviews: number;
  unfavorable_reviews: number;
  average_score: string | null;
  latest_reviewed_at: string | null;
};

export type ReviewFilters = {
  trade?: number | string;
  market?: number | string;
  account?: number | string;
  outcome?: TradeReviewOutcome;
  review_status?: TradeReviewStatus;
  ordering?: 'reviewed_at' | '-reviewed_at' | 'score' | '-score' | 'created_at' | '-created_at';
};

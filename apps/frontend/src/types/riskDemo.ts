export type TradeRiskDecision = 'APPROVE' | 'CAUTION' | 'BLOCK' | string;

export type TradeRiskWarning = {
  code: string;
  severity: 'low' | 'medium' | 'high' | string;
  message: string;
};

export type TradeRiskAssessment = {
  id: number;
  market: number;
  market_title: string;
  market_slug: string;
  paper_account: number | null;
  paper_account_slug: string | null;
  side: string;
  trade_type: string;
  quantity: string;
  requested_price: string | null;
  current_market_probability: string | null;
  current_yes_price: string | null;
  current_no_price: string | null;
  decision: TradeRiskDecision;
  score: string;
  confidence: string;
  summary: string;
  rationale: string;
  warnings: TradeRiskWarning[];
  suggested_quantity: string | null;
  is_actionable: boolean;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type AssessTradePayload = {
  market_id: number;
  trade_type: string;
  side: string;
  quantity: string;
  requested_price?: string | null;
  metadata?: Record<string, unknown>;
};

export type AssessTradeResponse = {
  assessment: TradeRiskAssessment;
};

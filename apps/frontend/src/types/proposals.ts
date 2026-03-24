export type TradeProposalDirection = 'BUY_YES' | 'BUY_NO' | 'HOLD' | 'AVOID' | string;

export type TradeProposalStatus = 'ACTIVE' | 'STALE' | 'SUPERSEDED' | 'REJECTED' | 'EXECUTED' | string;

export type GenerateTradeProposalPayload = {
  market_id: number;
  paper_account_id?: number | null;
  triggered_from?: 'market_detail' | 'signals' | 'dashboard' | 'automation' | string;
};

export type TradeProposal = {
  id: number;
  market: number;
  market_title: string;
  market_slug: string;
  paper_account: number | null;
  paper_account_slug: string | null;
  proposal_status: TradeProposalStatus;
  direction: TradeProposalDirection;
  proposal_score: string;
  confidence: string;
  headline: string;
  thesis: string;
  rationale: string;
  suggested_trade_type: 'BUY' | 'SELL' | 'HOLD' | string;
  suggested_side: 'YES' | 'NO' | null;
  suggested_quantity: string | null;
  suggested_price_reference: string | null;
  risk_decision: string;
  policy_decision: string;
  approval_required: boolean;
  is_actionable: boolean;
  recommendation: string;
  expires_at: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type TradeProposalFilters = {
  market: string;
  direction: string;
  is_actionable: string;
};

export type TradeProposalQueryParams = Partial<TradeProposalFilters>;

export type GenerateTradeProposalResponse = {
  proposal: TradeProposal;
};

export type PaperCurrency = 'USD' | string;
export type PaperSide = 'YES' | 'NO' | string;
export type PaperTradeType = 'BUY' | 'SELL' | string;
export type PaperTradeStatus = 'EXECUTED' | 'PENDING' | 'REJECTED' | string;
export type PaperPositionStatus = 'OPEN' | 'CLOSED' | string;

export type PaperAccount = {
  id: number;
  name: string;
  slug: string;
  currency: PaperCurrency;
  initial_balance: string;
  cash_balance: string;
  reserved_balance: string;
  equity: string;
  realized_pnl: string;
  unrealized_pnl: string;
  total_pnl: string;
  is_active: boolean;
  notes: string;
  open_positions_count: number;
  created_at: string;
  updated_at: string;
};

export type PaperPosition = {
  id: number;
  account: number;
  market: number;
  market_title: string;
  market_slug: string;
  market_status: string;
  side: PaperSide;
  quantity: string;
  average_entry_price: string;
  current_mark_price: string | null;
  cost_basis: string;
  market_value: string;
  realized_pnl: string;
  unrealized_pnl: string;
  status: PaperPositionStatus;
  opened_at: string | null;
  closed_at: string | null;
  last_marked_at: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type PaperTrade = {
  id: number;
  account: number;
  market: number;
  market_title: string;
  position: number | null;
  trade_type: PaperTradeType;
  side: PaperSide;
  quantity: string;
  price: string;
  gross_amount: string;
  fees: string;
  status: PaperTradeStatus;
  executed_at: string;
  notes: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type PaperPortfolioSnapshot = {
  id: number;
  account: number;
  captured_at: string;
  cash_balance: string;
  equity: string;
  realized_pnl: string;
  unrealized_pnl: string;
  total_pnl: string;
  open_positions_count: number;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type PaperPortfolioHistoryPoint = {
  id: number;
  capturedAt: string;
  capturedAtLabel: string;
  cashBalance: number | null;
  equity: number | null;
  realizedPnl: number | null;
  unrealizedPnl: number | null;
  totalPnl: number | null;
  openPositionsCount: number;
};

export type PaperExposureSummary = {
  market_id: number;
  market_title: string;
  side: PaperSide;
  quantity: string;
  market_value: string;
  unrealized_pnl: string;
  current_mark_price: string | null;
};

export type PaperRecentTradeSummary = {
  id: number;
  market_id: number;
  market__title: string;
  trade_type: PaperTradeType;
  side: PaperSide;
  quantity: string;
  price: string;
  gross_amount: string;
  status: PaperTradeStatus;
  executed_at: string;
};

export type PaperPortfolioSummary = {
  account: PaperAccount;
  open_positions_count: number;
  closed_positions_count: number;
  exposure_by_market: PaperExposureSummary[];
  recent_trades: PaperRecentTradeSummary[];
};

export type CreatePaperTradePayload = {
  market_id: number;
  trade_type: PaperTradeType;
  side: PaperSide;
  quantity: string;
  notes?: string;
  metadata?: Record<string, unknown>;
};

export type CreatePaperTradeResponse = {
  account: PaperAccount;
  position: PaperPosition;
  trade: PaperTrade;
};

export type MarketPaperPositionView = {
  marketId: number;
  marketTitle: string;
  positions: PaperPosition[];
  latestTrade: PaperTrade | null;
};

export type TradeExecutionState = {
  status: 'success' | 'error';
  message: string;
  response: CreatePaperTradeResponse | null;
};

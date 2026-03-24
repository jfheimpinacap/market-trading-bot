export type MarketProviderSummary = {
  id: number;
  name: string;
  slug: string;
  is_active: boolean;
};

export type MarketProvider = MarketProviderSummary & {
  description: string;
  base_url: string;
  api_base_url: string;
  notes: string;
  event_count: number;
  market_count: number;
  created_at: string;
  updated_at: string;
};

export type MarketEvent = {
  id: number;
  provider: MarketProviderSummary;
  provider_event_id: string;
  title: string;
  slug: string;
  category: string;
  status: string;
  source_type: 'demo' | 'real_read_only' | string;
  open_time: string | null;
  close_time: string | null;
  resolution_time: string | null;
  market_count: number;
  description?: string;
  metadata?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type MarketRule = {
  id: number;
  source_type: string;
  rule_text: string;
  resolution_criteria: string;
  created_at: string;
  updated_at: string;
};

export type MarketSnapshot = {
  id: number;
  market_id: number;
  captured_at: string;
  market_probability: string | null;
  yes_price: string | null;
  no_price: string | null;
  last_price: string | null;
  bid: string | null;
  ask: string | null;
  spread: string | null;
  liquidity: string | null;
  volume: string | null;
  volume_24h: string | null;
  open_interest: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type MarketHistoryPoint = {
  id: number;
  capturedAt: string;
  capturedAtLabel: string;
  marketProbability: number | null;
  yesPrice: number | null;
  noPrice: number | null;
  liquidity: number | null;
};

export type MarketListItem = {
  id: number;
  provider: MarketProviderSummary;
  event_id: number | null;
  event_title: string | null;
  provider_market_id: string;
  ticker: string;
  title: string;
  slug: string;
  category: string;
  market_type: string;
  outcome_type: string;
  status: string;
  resolution_source: string;
  url: string | null;
  is_active: boolean;
  open_time: string | null;
  close_time: string | null;
  resolution_time: string | null;
  current_market_probability: string | null;
  current_yes_price: string | null;
  current_no_price: string | null;
  liquidity: string | null;
  volume_24h: string | null;
  volume_total: string | null;
  spread_bps: string | null;
  source_type: 'demo' | 'real_read_only' | string;
  is_demo: boolean;
  is_real: boolean;
  snapshot_count: number;
  latest_snapshot_at: string | null;
  created_at: string;
  updated_at: string;
};

export type MarketDetail = MarketListItem & {
  event: MarketEvent | null;
  short_rules: string;
  metadata: Record<string, unknown>;
  rules: MarketRule[];
  recent_snapshots: MarketSnapshot[];
};

export type MarketSystemSummary = {
  total_providers: number;
  total_events: number;
  total_markets: number;
  active_markets: number;
  resolved_markets: number;
  total_snapshots: number;
};

export type MarketFilters = {
  source_type: string;
  provider: string;
  category: string;
  status: string;
  is_active: string;
  search: string;
  ordering: string;
};

export type MarketQueryParams = Partial<MarketFilters> & {
  event?: string;
};

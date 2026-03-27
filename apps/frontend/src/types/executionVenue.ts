export type VenueCapabilityProfile = {
  id: number;
  adapter_name: string;
  venue_name: string;
  supports_market_like: boolean;
  supports_limit_like: boolean;
  supports_reduce_only: boolean;
  supports_close_order: boolean;
  supports_partial_updates: boolean;
  requires_symbol_mapping: boolean;
  requires_manual_confirmation: boolean;
  paper_only_supported: boolean;
  live_supported: boolean;
  metadata: Record<string, unknown>;
  updated_at: string;
};

export type VenueOrderPayload = {
  id: number;
  intent: number;
  venue_name: string;
  external_market_id: string;
  side: string;
  order_type: string;
  quantity: string;
  limit_price: string | null;
  tif: string;
  reduce_only: boolean;
  close_flag: boolean;
  source_intent_id: number;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type VenueOrderResponse = {
  id: number;
  intent: number;
  payload: number | null;
  external_order_id: string | null;
  normalized_status: 'ACCEPTED' | 'REJECTED' | 'HOLD' | 'REQUIRES_CONFIRMATION' | 'UNSUPPORTED' | 'INVALID_PAYLOAD';
  reason_codes: string[];
  warnings: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type VenueParityRun = {
  id: number;
  intent: number;
  payload: VenueOrderPayload | null;
  response: VenueOrderResponse | null;
  parity_status: 'PARITY_OK' | 'PARITY_GAP';
  issues: string[];
  missing_fields: string[];
  unsupported_actions: string[];
  readiness_score: number;
  bridge_dry_run_id: number | null;
  simulator_order_id: number | null;
  created_at: string;
};

export type VenueSummary = {
  adapter: string;
  sandbox_only: boolean;
  total_runs: number;
  parity_ok: number;
  parity_gap: number;
  avg_readiness_score: number;
  latest_run_id: number | null;
  latest_parity_status: string | null;
};

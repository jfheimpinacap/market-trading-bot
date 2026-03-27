export type VenueAccountSnapshot = {
  id: number;
  venue_name: string;
  account_reference: string;
  account_mode: 'SANDBOX_ONLY';
  equity: string;
  cash_available: string;
  reserved_cash: string;
  open_positions_count: number;
  open_orders_count: number;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type VenueBalanceSnapshot = {
  id: number;
  account_snapshot: number;
  currency: string;
  available: string;
  reserved: string;
  total: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type VenueOrderSnapshot = {
  id: number;
  source_intent: number | null;
  source_paper_order: number | null;
  source_intent_ref_id: number | null;
  external_order_id: string;
  instrument_ref: string;
  side: string;
  quantity: string;
  filled_quantity: string;
  remaining_quantity: string;
  status: 'NEW' | 'OPEN' | 'PARTIALLY_FILLED' | 'FILLED' | 'CANCELLED' | 'EXPIRED' | 'REJECTED';
  last_response_status: string;
  metadata: Record<string, unknown>;
  updated_at: string;
};

export type VenuePositionSnapshot = {
  id: number;
  external_instrument_ref: string;
  side: string;
  quantity: string;
  avg_entry_price: string;
  unrealized_pnl: string | null;
  source_internal_position: number | null;
  status: 'OPEN' | 'CLOSED';
  metadata: Record<string, unknown>;
  updated_at: string;
};

export type VenueReconciliationIssue = {
  id: number;
  reconciliation_run: number;
  issue_type: string;
  severity: 'INFO' | 'WARNING' | 'HIGH';
  reason: string;
  source_refs: Record<string, unknown>;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type VenueReconciliationRun = {
  id: number;
  status: 'PARITY_OK' | 'PARITY_GAP';
  positions_compared: number;
  orders_compared: number;
  balances_compared: number;
  mismatches_count: number;
  summary: string;
  details: Record<string, unknown>;
  issues: VenueReconciliationIssue[];
  created_at: string;
};

export type VenueAccountSummary = {
  sandbox_only: boolean;
  account_snapshot: {
    id: number;
    venue_name: string;
    account_mode: string;
    equity: string;
    cash_available: string;
    reserved_cash: string;
    open_positions_count: number;
    open_orders_count: number;
    created_at: string;
  } | null;
  latest_reconciliation: {
    id: number;
    status: string;
    mismatches_count: number;
    created_at: string;
  } | null;
  recent_issues: Array<{ id: number; issue_type: string; severity: string; reason: string; created_at: string; run_id: number }>;
};

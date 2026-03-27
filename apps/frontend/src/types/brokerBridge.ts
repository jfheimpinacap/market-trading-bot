export type BrokerBridgeValidation = {
  id: number;
  outcome: 'VALID' | 'INVALID' | 'MANUAL_REVIEW';
  is_valid: boolean;
  requires_manual_review: boolean;
  blocking_reasons: string[];
  warnings: string[];
  missing_fields: string[];
  checks: Record<string, unknown>;
  created_at: string;
};

export type BrokerDryRun = {
  id: number;
  simulated_response: 'accepted' | 'rejected' | 'hold' | 'needs_manual_review';
  dry_run_summary: string;
  simulated_payload: Record<string, unknown>;
  simulated_broker_response: Record<string, unknown>;
  created_at: string;
};

export type BrokerOrderIntent = {
  id: number;
  source_type: string;
  source_id: string;
  source_ref: string;
  market: number | null;
  market_title?: string;
  market_ref: string;
  symbol: string;
  side: string;
  order_type: string;
  quantity: string;
  limit_price: string | null;
  time_in_force: string;
  status: 'DRAFT' | 'VALIDATED' | 'REJECTED' | 'DRY_RUN_READY' | 'DRY_RUN_EXECUTED';
  mapping_profile: string;
  created_at: string;
  validations: BrokerBridgeValidation[];
  dry_runs: BrokerDryRun[];
};

export type BrokerBridgeSummary = {
  intents_created: number;
  validated: number;
  rejected: number;
  dry_run_accepted: number;
  dry_run_manual_review: number;
  status_counts: Record<string, number>;
  dry_run_response_counts: Record<string, number>;
};

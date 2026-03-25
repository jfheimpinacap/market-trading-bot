export type RealMarketOpRunStatus = 'SUCCESS' | 'PARTIAL' | 'FAILED' | 'SKIPPED';

export type RealMarketOpsEvaluateResponse = {
  scope: Record<string, unknown>;
  providers_considered: string[];
  provider_status: Record<string, unknown>;
  markets_considered: number;
  markets_eligible: number;
  excluded_count: number;
  skipped_stale_count: number;
  skipped_degraded_provider_count: number;
  skipped_no_pricing_count: number;
  eligible_markets: Array<Record<string, unknown>>;
  excluded_markets: Array<Record<string, unknown>>;
};

export type RealMarketOpRun = {
  id: number;
  status: RealMarketOpRunStatus;
  triggered_from: 'continuous_demo' | 'automation' | 'manual';
  started_at: string;
  finished_at: string | null;
  providers_considered: number;
  markets_considered: number;
  markets_eligible: number;
  proposals_generated: number;
  auto_executed_count: number;
  approval_required_count: number;
  blocked_count: number;
  skipped_stale_count: number;
  skipped_degraded_provider_count: number;
  skipped_no_pricing_count: number;
  summary: string;
  details: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type RealMarketOpsStatus = {
  enabled: boolean;
  execution_mode: string;
  source_type_required: string;
  provider_status: Record<string, unknown>;
  scope: Record<string, unknown>;
  latest_run: RealMarketOpRun | null;
};

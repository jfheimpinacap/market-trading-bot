export type RealSyncProvider = 'kalshi' | 'polymarket';
export type RealSyncType = 'full' | 'incremental' | 'single_market' | 'active_only';
export type RealSyncStatus = 'RUNNING' | 'SUCCESS' | 'PARTIAL' | 'FAILED';

export type RealSyncRun = {
  id: number;
  provider: RealSyncProvider;
  sync_type: RealSyncType;
  status: RealSyncStatus;
  started_at: string;
  finished_at: string | null;
  triggered_from: string;
  markets_seen: number;
  markets_created: number;
  markets_updated: number;
  snapshots_created: number;
  errors_count: number;
  summary: string;
  details: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type RunRealSyncPayload = {
  provider: RealSyncProvider;
  sync_type?: RealSyncType;
  active_only?: boolean;
  limit?: number;
  market_id?: string;
  triggered_from?: string;
};

export type RealSyncProviderStatus = {
  provider: RealSyncProvider;
  latest_run_id: number | null;
  latest_status: RealSyncStatus | null;
  latest_started_at: string | null;
  last_success_at: string | null;
  last_failed_at: string | null;
  consecutive_failures: number;
  stale: boolean;
  availability: 'available' | 'degraded' | 'unknown';
  warning: string;
};

export type RealSyncStatusResponse = {
  providers: Record<RealSyncProvider, RealSyncProviderStatus>;
  stale_after_minutes: number;
};

export type RealSyncSummary = {
  total_runs: number;
  by_status: Record<string, number>;
  by_provider: Record<string, number>;
};

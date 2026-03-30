export type ScanSignalStatus = 'candidate' | 'shortlisted' | 'watch' | 'ignore' | string;
export type ScanClusterStatus = 'emerging' | 'confirmed_multi_source' | 'noisy' | 'stale' | string;

export type SourceScanRun = {
  id: number;
  started_at: string;
  completed_at: string | null;
  source_counts: { rss_count?: number; reddit_count?: number; x_count?: number };
  raw_item_count: number;
  deduped_item_count: number;
  clustered_count: number;
  signal_count: number;
  ignored_count: number;
  recommendation_summary: Record<string, number>;
  metadata: Record<string, unknown>;
};

export type NarrativeSignal = {
  id: number;
  canonical_label: string;
  topic: string;
  source_mix: { source_types?: string[]; source_count?: number; item_count?: number };
  direction: string;
  novelty_score: string;
  intensity_score: string;
  market_divergence_score: string;
  total_signal_score: string;
  status: ScanSignalStatus;
  rationale: string;
  reason_codes: string[];
  linked_market: number | null;
  linked_market_slug?: string;
  linked_cluster: number | null;
};

export type NarrativeCluster = {
  id: number;
  canonical_topic: string;
  representative_headline: string;
  item_count: number;
  source_types: string[];
  cluster_status: ScanClusterStatus;
};

export type ScanRecommendation = {
  id: number;
  recommendation_type: string;
  target_signal: number | null;
  target_signal_label: string;
  rationale: string;
  reason_codes: string[];
  confidence: string;
  blockers: string[];
};

export type ScanSummary = {
  run_count: number;
  signal_count: number;
  shortlisted_signal_count: number;
  watch_signal_count: number;
  ignored_signal_count: number;
  cluster_count: number;
  latest_run: SourceScanRun | null;
  latest_recommendations: ScanRecommendation[];
};

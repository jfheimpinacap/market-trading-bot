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

export type NarrativeConsensusRun = {
  id: number;
  started_at: string;
  completed_at: string | null;
  considered_signal_count: number;
  considered_cluster_count: number;
  consensus_detected_count: number;
  conflict_detected_count: number;
  divergence_detected_count: number;
  priority_handoff_count: number;
  recommendation_summary: Record<string, number>;
};

export type NarrativeConsensusRecord = {
  id: number;
  topic_label: string;
  source_mix: Record<string, unknown>;
  source_count: number;
  consensus_state: string;
  sentiment_direction: string;
  intensity_score: string;
  novelty_score: string;
  persistence_score: string;
  confidence_score: string;
  summary: string;
};

export type NarrativeMarketDivergenceRecord = {
  id: number;
  linked_market_title?: string;
  narrative_bias: string;
  market_probability: string | null;
  divergence_state: string;
  divergence_score: string;
  market_context_summary: string;
};

export type ResearchHandoffPriority = {
  id: number;
  topic_label?: string;
  linked_market_title?: string;
  priority_bucket: string;
  handoff_status: string;
  priority_reason_codes: string[];
  priority_score: string;
  handoff_summary: string;
};

export type NarrativeConsensusRecommendation = {
  id: number;
  recommendation_type: string;
  rationale: string;
  reason_codes: string[];
  confidence: string;
  blockers: string[];
};

export type ConsensusSummary = {
  latest_run: number | null;
  signals_considered: number;
  clusters_considered: number;
  strong_consensus_count: number;
  conflicted_count: number;
  high_divergence_count: number;
  ready_for_research_count: number;
  recommendation_summary: Record<string, number>;
};

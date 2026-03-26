export type NarrativeSentiment = 'bullish' | 'bearish' | 'neutral' | 'mixed' | 'uncertain';

export type ResearchSource = {
  id: number;
  name: string;
  slug: string;
  source_type: 'rss' | 'reddit' | 'news_api' | 'twitter' | 'manual' | string;
  feed_url: string;
  is_enabled: boolean;
  language: string;
  category: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type NarrativeAnalysis = {
  id: number;
  summary: string;
  sentiment: NarrativeSentiment;
  confidence: string;
  entities: string[];
  topics: string[];
  market_relevance_score: string;
  analysis_status: string;
  model_name: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type NarrativeItem = {
  id: number;
  source: number;
  source_name: string;
  source_type: ResearchSource['source_type'];
  external_id: string | null;
  title: string;
  url: string;
  published_at: string | null;
  raw_text: string;
  snippet: string;
  author: string;
  dedupe_hash: string;
  ingested_at: string;
  metadata: Record<string, unknown>;
  analysis?: NarrativeAnalysis;
  linked_market_count: number;
  created_at: string;
  updated_at: string;
};

export type ResearchCandidate = {
  id: number;
  market: number;
  market_slug: string;
  market_title: string;
  narrative_pressure: string;
  sentiment_direction: NarrativeSentiment;
  implied_probability_snapshot: string | null;
  market_implied_direction: NarrativeSentiment;
  relation: 'alignment' | 'divergence' | 'uncertainty';
  divergence_score: string;
  rss_narrative_contribution: string;
  social_narrative_contribution: string;
  source_mix: 'news_only' | 'social_only' | 'mixed' | 'social_heavy' | 'news_confirmed' | string;
  short_thesis: string;
  priority: string;
  metadata: Record<string, unknown>;
  linked_item_count: number;
  created_at: string;
  updated_at: string;
};

export type ResearchScanRun = {
  id: number;
  status: 'success' | 'partial' | 'failed';
  triggered_by: string;
  sources_scanned: number;
  items_created: number;
  rss_items_created: number;
  reddit_items_created: number;
  items_deduplicated: number;
  analyses_generated: number;
  analyses_degraded: number;
  candidates_generated: number;
  started_at: string;
  finished_at: string | null;
  errors: string[];
  source_errors: Record<string, string[]>;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type ResearchSummary = {
  source_count: number;
  rss_source_count: number;
  reddit_source_count: number;
  item_count: number;
  rss_item_count: number;
  reddit_item_count: number;
  analyzed_count: number;
  candidate_count: number;
  mixed_candidate_count: number;
  latest_run: ResearchScanRun | null;
};

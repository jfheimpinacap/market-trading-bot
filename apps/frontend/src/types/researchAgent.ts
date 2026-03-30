export type ResearchUniverseSummary = {
  latest_run: { id: number; started_at: string; completed_at: string | null } | null;
  totals: {
    total_markets_seen: number;
    open_markets_seen: number;
    shortlisted_count: number;
    watchlist_count: number;
    ignored_count: number;
    sent_to_prediction_count: number;
  };
  recommendation_summary: Record<string, number>;
};

export type MarketResearchCandidate = {
  id: number;
  universe_run: number;
  linked_market: number;
  market_slug: string;
  market_title: string;
  market_provider: string;
  category: string;
  end_time: string | null;
  time_to_resolution_hours: number | null;
  liquidity_score: string;
  volume_score: string;
  freshness_score: string;
  market_quality_score: string;
  narrative_support_score: string;
  divergence_score: string;
  pursue_worthiness_score: string;
  status: 'shortlist' | 'watchlist' | 'ignore' | 'needs_review';
  rationale: string;
  reason_codes: string[];
  linked_narrative_signals: Array<{ id: number; label: string; status: string; total_signal_score: string }>;
  metadata: Record<string, unknown>;
};

export type MarketTriageDecision = {
  id: number;
  linked_candidate: number;
  market_title: string;
  decision_type: string;
  decision_status: string;
  rationale: string;
  reason_codes: string[];
  blockers: string[];
  metadata: Record<string, unknown>;
};

export type MarketResearchRecommendation = {
  id: number;
  universe_run: number;
  recommendation_type: string;
  target_market: number | null;
  target_candidate: number | null;
  market_title: string;
  rationale: string;
  reason_codes: string[];
  confidence: string;
  blockers: string[];
  metadata: Record<string, unknown>;
};

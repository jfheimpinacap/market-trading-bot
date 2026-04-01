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

export type ResearchPursuitSummary = {
  latest_run: { id: number; started_at: string; completed_at: string | null } | null;
  totals: {
    markets_considered: number;
    prediction_ready: number;
    watchlist: number;
    deferred: number;
    blocked: number;
    high_priority_divergence: number;
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

export type ResearchStructuralAssessment = {
  id: number;
  market_title: string;
  market_slug: string;
  liquidity_state: string;
  volume_state: string;
  time_to_resolution_state: string;
  market_activity_state: string;
  structural_status: string;
  assessment_summary: string;
  reason_codes: string[];
};

export type ResearchPursuitScore = {
  id: number;
  market_title: string;
  market_slug: string;
  pursuit_score: string;
  priority_bucket: string;
  score_status: string;
  score_components: Record<string, string>;
  score_summary: string;
};

export type PredictionHandoffCandidate = {
  id: number;
  market_title: string;
  market_slug: string;
  handoff_status: string;
  handoff_confidence: string;
  handoff_summary: string;
  handoff_reason_codes: string[];
};

export type ResearchPursuitRecommendation = {
  id: number;
  recommendation_type: string;
  market_title: string;
  confidence: string;
  reason_codes: string[];
  blockers: string[];
  rationale: string;
};

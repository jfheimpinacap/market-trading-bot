export type LearningOutcome = 'positive' | 'neutral' | 'negative';

export type LearningMemoryEntry = {
  id: number;
  memory_type: string;
  source_type: string;
  provider: number | null;
  provider_slug?: string;
  market: number | null;
  market_slug?: string;
  related_trade: number | null;
  related_review: number | null;
  related_signal: number | null;
  signal_type?: string;
  outcome: LearningOutcome;
  score_delta: string;
  confidence_delta: string;
  quantity_bias_delta: string;
  summary: string;
  rationale: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type LearningAdjustment = {
  id: number;
  adjustment_type: string;
  scope_type: string;
  scope_key: string;
  is_active: boolean;
  magnitude: string;
  reason: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type LearningSummary = {
  total_memory_entries: number;
  active_adjustments: number;
  negative_patterns_detected: number;
  conservative_bias_score: string;
  entries_by_outcome: Record<string, number>;
  adjustments_by_scope: Record<string, number>;
  recent_memory: LearningMemoryEntry[];
  recent_adjustments: LearningAdjustment[];
};

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

export type LearningLoopSummary = {
  runs_processed: number;
  active_patterns: number;
  active_adjustments: number;
  expired_adjustments: number;
  applications_recorded: number;
  manual_review_required: boolean;
  latest_run: PostmortemLearningRun | null;
};

export type FailurePattern = {
  id: number;
  canonical_label: string;
  pattern_type: string;
  scope: string;
  scope_key: string;
  severity_score: string;
  recurrence_count: number;
  status: 'ACTIVE' | 'WATCH' | 'EXPIRED' | 'NEEDS_REVIEW';
  rationale: string;
  reason_codes: string[];
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type LearningAdjustment = {
  id: number;
  linked_failure_pattern: number | null;
  linked_postmortem: number | null;
  adjustment_type: string;
  scope: string;
  scope_key: string;
  adjustment_strength: string;
  status: 'PROPOSED' | 'ACTIVE' | 'PAUSED' | 'EXPIRED' | 'REJECTED';
  expiration_hint: string | null;
  rationale: string;
  reason_codes: string[];
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type LearningApplicationRecord = {
  id: number;
  linked_adjustment: number;
  target_component: 'research' | 'prediction' | 'risk' | 'proposal' | 'signal_fusion';
  target_entity_id: string;
  application_type: string;
  before_value: string;
  after_value: string;
  rationale: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type LearningRecommendation = {
  id: number;
  recommendation_type: string;
  target_pattern: number | null;
  target_adjustment: number | null;
  rationale: string;
  reason_codes: string[];
  confidence: string;
  blockers: string[];
  created_at: string;
};

export type PostmortemLearningRun = {
  id: number;
  linked_postmortem_run: number | null;
  started_at: string;
  completed_at: string | null;
  reviewed_position_count: number;
  failure_pattern_count: number;
  adjustment_count: number;
  active_adjustment_count: number;
  expired_adjustment_count: number;
  recommendation_summary: string;
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

export type LearningRebuildRunStatus = 'SUCCESS' | 'PARTIAL' | 'FAILED';
export type LearningRebuildTriggeredFrom = 'manual' | 'automation' | 'continuous_demo' | 'evaluation' | 'postmortem';

export type LearningRebuildRun = {
  id: number;
  status: LearningRebuildRunStatus;
  triggered_from: LearningRebuildTriggeredFrom;
  related_session: number | null;
  related_cycle: number | null;
  started_at: string;
  finished_at: string | null;
  memory_entries_processed: number;
  adjustments_created: number;
  adjustments_updated: number;
  adjustments_deactivated: number;
  summary: string;
  details: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type LearningIntegrationStatus = {
  learning_rebuild_enabled: boolean;
  learning_rebuild_every_n_cycles: number;
  learning_rebuild_after_reviews: boolean;
  latest_rebuild_run: LearningRebuildRun | null;
  message: string;
};

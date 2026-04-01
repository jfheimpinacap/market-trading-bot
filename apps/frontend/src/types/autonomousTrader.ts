export type AutonomousTraderSummary = {
  latest_run_id: number | null;
  considered_candidate_count: number;
  watchlist_count: number;
  approved_for_execution_count: number;
  executed_paper_trade_count: number;
  blocked_count: number;
  closed_position_count: number;
  postmortem_handoff_count: number;
  recommendation_summary: Record<string, number>;
};

export type AutonomousExecutionIntakeSummary = {
  latest_run_id: number | null;
  considered_readiness_count: number;
  execute_now_count: number;
  execute_reduced_count: number;
  watch_count: number;
  defer_count: number;
  blocked_count: number;
  manual_review_count: number;
  dispatch_count: number;
  recommendation_summary: Record<string, number>;
};

export type AutonomousExecutionIntakeCandidate = {
  id: number;
  market_title: string;
  readiness_confidence: string;
  approval_status: string;
  sizing_method: string;
  intake_status: string;
  execution_context_summary: string;
};

export type AutonomousExecutionDecision = {
  id: number;
  market_title: string;
  decision_type: string;
  decision_status: string;
  decision_confidence: string;
  rationale: string;
};

export type AutonomousDispatchRecord = {
  id: number;
  market_title: string;
  dispatch_status: string;
  dispatch_mode: string;
  dispatched_quantity: string | null;
  dispatched_notional: string | null;
  dispatch_summary: string;
};

export type AutonomousExecutionRecommendation = {
  id: number;
  recommendation_type: string;
  rationale: string;
  blockers: string[];
  confidence: string;
};

export type AutonomousOutcomeHandoffSummary = {
  latest_run_id: number | null;
  considered_outcome_count: number;
  eligible_postmortem_count: number;
  eligible_learning_count: number;
  postmortem_handoff_created_count: number;
  learning_handoff_created_count: number;
  emitted_count: number;
  duplicate_skipped_count: number;
  blocked_count: number;
  recommendation_summary: Record<string, number>;
};

export type AutonomousTradeCandidate = {
  id: number;
  market_title: string;
  adjusted_edge: string;
  confidence: string;
  candidate_status: string;
  risk_posture: string;
};

export type AutonomousTradeDecision = {
  id: number;
  market_title: string;
  decision_type: string;
  rationale: string;
  decision_status: string;
};

export type AutonomousTradeExecution = {
  id: number;
  market_title: string;
  execution_status: string;
  sizing_summary: string;
  linked_paper_trade: number | null;
};

export type AutonomousTradeWatchRecord = {
  id: number;
  market_title: string;
  watch_status: string;
  sentiment_shift_detected: boolean;
  market_move_detected: boolean;
  risk_change_detected: boolean;
};

export type AutonomousTradeOutcome = {
  id: number;
  market_title: string;
  outcome_type: string;
  outcome_status: string;
  send_to_postmortem: boolean;
  send_to_learning: boolean;
};

export type AutonomousPostmortemHandoff = {
  id: number;
  linked_outcome: number;
  trigger_reason: string;
  handoff_status: string;
  linked_postmortem_run: number | null;
  handoff_summary: string;
};

export type AutonomousLearningHandoff = {
  id: number;
  linked_outcome: number;
  trigger_reason: string;
  handoff_status: string;
  linked_learning_run: number | null;
  handoff_summary: string;
};

export type AutonomousOutcomeHandoffRecommendation = {
  id: number;
  recommendation_type: string;
  rationale: string;
  blockers: string[];
  confidence: string;
};

export type AutonomousFeedbackSummary = {
  latest_run_id: number | null;
  considered_candidate_count: number;
  retrieval_hit_count: number;
  influence_applied_count: number;
  watch_caution_count: number;
  blocked_or_reduced_count: number;
  no_relevant_learning_found_count: number;
  recommendation_summary: Record<string, number>;
};

export type AutonomousFeedbackCandidateContext = {
  id: number;
  linked_candidate: number;
  market_title: string;
  retrieval_status: string;
  top_precedent_count: number;
  context_summary: string;
};

export type AutonomousFeedbackInfluence = {
  id: number;
  market_title: string;
  influence_type: string;
  influence_status: string;
  influence_reason_codes: string[];
  pre_adjust_confidence: string | null;
  post_adjust_confidence: string | null;
  influence_summary: string;
};

export type AutonomousFeedbackRecommendation = {
  id: number;
  recommendation_type: string;
  rationale: string;
  blockers: string[];
  confidence: string;
};

export type AutonomousSizingSummary = {
  latest_run_id: number | null;
  considered_candidate_count: number;
  approved_for_sizing_count: number;
  reduced_by_portfolio_count: number;
  reduced_by_risk_count: number;
  blocked_for_sizing_count: number;
  sized_for_execution_count: number;
  recommendation_summary: Record<string, number>;
};

export type AutonomousSizingContext = {
  id: number;
  market_title: string;
  adjusted_edge: string;
  confidence: string;
  uncertainty: string | null;
  risk_posture: string;
  portfolio_posture: string;
  context_status: string;
};

export type AutonomousSizingDecision = {
  id: number;
  market_title: string;
  sizing_method: string;
  decision_status: string;
  base_kelly_fraction: string | null;
  applied_fraction: string | null;
  notional_before_adjustment: string | null;
  notional_after_adjustment: string | null;
  final_paper_quantity: string | null;
  decision_summary: string;
};

export type AutonomousSizingRecommendation = {
  id: number;
  recommendation_type: string;
  rationale: string;
  blockers: string[];
  confidence: string;
};

export type AutonomousPositionWatchSummary = {
  latest_run_id: number | null;
  considered_position_count: number;
  hold_count: number;
  reduce_count: number;
  close_count: number;
  review_required_count: number;
  executed_reduce_count: number;
  executed_close_count: number;
  recommendation_summary: Record<string, number>;
};

export type AutonomousPositionWatchCandidate = {
  id: number;
  market_title: string;
  candidate_status: string;
  entry_probability: string | null;
  current_probability: string | null;
  entry_edge: string | null;
  current_edge: string | null;
  sentiment_state: string;
  risk_state: string;
  portfolio_pressure_state: string;
};

export type AutonomousPositionActionDecision = {
  id: number;
  market_title: string;
  decision_type: string;
  decision_status: string;
  decision_confidence: string;
  reduction_fraction: string | null;
  rationale: string;
};

export type AutonomousPositionActionExecution = {
  id: number;
  market_title: string;
  execution_type: string;
  execution_status: string;
  quantity_before: string | null;
  quantity_after: string | null;
  notional_before: string | null;
  notional_after: string | null;
  summary: string;
};

export type AutonomousPositionWatchRecommendation = {
  id: number;
  recommendation_type: string;
  rationale: string;
  blockers: string[];
  confidence: string;
};

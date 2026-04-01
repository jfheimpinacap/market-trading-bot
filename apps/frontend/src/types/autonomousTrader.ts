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

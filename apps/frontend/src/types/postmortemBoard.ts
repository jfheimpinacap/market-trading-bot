export type PostmortemBoardRunStatus = 'READY' | 'RUNNING' | 'SUCCESS' | 'PARTIAL' | 'FAILED';
export type PostmortemReviewStatus = 'SUCCESS' | 'PARTIAL' | 'FAILED' | 'SKIPPED';
export type PostmortemPerspectiveType = 'narrative' | 'prediction' | 'risk' | 'runtime' | 'learning';

export interface PostmortemBoardRun {
  id: number;
  related_trade_review: number;
  trade_review_id: number;
  trade_id: number;
  market_id: number;
  status: PostmortemBoardRunStatus;
  started_at: string | null;
  finished_at: string | null;
  perspectives_run_count: number;
  summary: string;
  details: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface PostmortemAgentReview {
  id: number;
  board_run: number;
  board_run_id: number;
  perspective_type: PostmortemPerspectiveType;
  status: PostmortemReviewStatus;
  conclusion: string;
  key_findings: Record<string, unknown>;
  confidence: string;
  recommended_actions: string[];
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface PostmortemBoardConclusion {
  id: number;
  board_run: number;
  board_run_id: number;
  primary_failure_mode: string;
  secondary_failure_modes: string[];
  lesson_learned: string;
  recommended_adjustments: string[];
  should_update_learning_memory: boolean;
  severity: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface PostmortemBoardSummary {
  total_runs: number;
  runs_by_status: Record<string, number>;
  average_perspectives: number | null;
  latest_run: PostmortemBoardRun | null;
  total_reviews: number;
  total_conclusions: number;
}

export interface RunPostmortemBoardPayload {
  related_trade_review_id: number;
  force_learning_rebuild?: boolean;
  triggered_from?: 'manual' | 'automation' | 'continuous_demo';
}

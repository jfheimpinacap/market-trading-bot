export type AllocationScopeType = 'real_only' | 'demo_only' | 'mixed';

export type AllocationDecisionType = 'SELECTED' | 'REDUCED' | 'SKIPPED' | 'REJECTED';

export type AllocationEvaluatePayload = {
  scope_type?: AllocationScopeType;
  max_candidates?: number;
  max_executions?: number;
  triggered_from?: string;
};

export type AllocationRankedDecision = {
  proposal_id: number;
  market: string;
  direction: string;
  proposal_score: string;
  confidence: string;
  suggested_quantity: string;
  final_allocated_quantity: string;
  decision: AllocationDecisionType;
  rank: number;
  source_type: string;
  provider: string;
  rationale: string[];
};

export type AllocationEvaluateResponse = {
  scope_type: AllocationScopeType;
  triggered_from: string;
  proposals_considered: number;
  proposals_ranked: number;
  proposals_selected: number;
  proposals_rejected: number;
  allocated_total: string;
  remaining_cash: string;
  summary: string;
  details: AllocationRankedDecision[];
  run_id: number | null;
};

export type AllocationDecision = {
  id: number;
  proposal: number;
  proposal_headline: string;
  market_title: string;
  direction: string;
  proposal_score: string;
  confidence: string;
  suggested_quantity: string;
  source_type: string;
  provider: string;
  rank: number;
  final_allocated_quantity: string;
  decision: AllocationDecisionType;
  rationale: string;
  details: Record<string, string>;
  created_at: string;
};

export type AllocationRun = {
  id: number;
  status: string;
  scope_type: AllocationScopeType;
  triggered_from: string;
  started_at: string;
  finished_at: string | null;
  proposals_considered: number;
  proposals_ranked: number;
  proposals_selected: number;
  proposals_rejected: number;
  allocated_total: string;
  remaining_cash: string;
  summary: string;
  details: Record<string, unknown>;
  decisions: AllocationDecision[];
};

export type AllocationSummary = {
  total_runs: number;
  latest_run: AllocationRun | null;
  selected_total: number;
  rejected_total: number;
  allocated_total: string;
};

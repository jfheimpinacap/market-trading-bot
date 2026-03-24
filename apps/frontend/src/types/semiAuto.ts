export type SemiAutoRunType = 'scan_and_execute' | 'execute_auto' | 'evaluate_only';
export type SemiAutoRunStatus = 'RUNNING' | 'SUCCESS' | 'PARTIAL' | 'FAILED';
export type PendingApprovalStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'EXPIRED' | 'EXECUTED';

export type SemiAutoEvaluationResult = {
  market_id?: number;
  market_title?: string;
  proposal_id?: number;
  policy_decision?: string;
  risk_decision?: string;
  is_actionable?: boolean;
  classification?: 'auto_executable' | 'approval_required' | 'blocked';
  action?: string;
  reasons?: string[];
  pending_approval_id?: number;
  trade_id?: number;
};

export type SemiAutoRun = {
  id: number;
  run_type: SemiAutoRunType;
  status: SemiAutoRunStatus;
  started_at: string;
  finished_at: string | null;
  markets_evaluated: number;
  proposals_generated: number;
  auto_executed_count: number;
  approval_required_count: number;
  blocked_count: number;
  summary: string;
  details: {
    results?: SemiAutoEvaluationResult[];
    guardrails?: Record<string, string | number | boolean>;
  };
  created_at: string;
  updated_at: string;
};

export type PendingApproval = {
  id: number;
  proposal: number;
  proposal_headline: string;
  proposal_thesis: string;
  market: number;
  market_title: string;
  paper_account: number;
  status: PendingApprovalStatus;
  requested_action: 'BUY' | 'SELL';
  suggested_side: 'YES' | 'NO';
  suggested_quantity: string;
  policy_decision: string;
  summary: string;
  rationale: string;
  decided_at: string | null;
  decision_note: string;
  metadata: Record<string, unknown>;
  executed_trade: { id: number } | null;
  created_at: string;
  updated_at: string;
};

export type SemiAutoSummary = {
  latest_run: SemiAutoRun | null;
  pending_count: number;
  executed_count: number;
  rejected_count: number;
  safety: Record<string, string | number | boolean>;
};

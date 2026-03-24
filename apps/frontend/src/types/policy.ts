export type PolicyDecisionType = 'AUTO_APPROVE' | 'APPROVAL_REQUIRED' | 'HARD_BLOCK' | string;
export type PolicySeverity = 'LOW' | 'MEDIUM' | 'HIGH' | string;
export type PolicyTriggeredFrom = 'market_detail' | 'automation' | 'signal' | 'system' | string;
export type PolicyRequestedBy = 'user' | 'automation_demo' | 'system' | string;

export type PolicyMatchedRule = {
  code: string;
  title: string;
  outcome: PolicyDecisionType;
  severity: PolicySeverity;
  message: string;
  recommendation: string;
};

export type TradePolicyEvaluation = {
  id: number;
  market: number;
  market_title: string;
  market_slug: string;
  market_source_type?: 'demo' | 'real_read_only' | string;
  execution_mode?: 'paper_demo_only' | string;
  paper_account: number | null;
  paper_account_slug: string | null;
  risk_assessment: number | null;
  linked_signal_id: number | null;
  trade_type: string;
  side: string;
  quantity: string;
  requested_price: string | null;
  estimated_gross_amount: string | null;
  requested_by: PolicyRequestedBy;
  triggered_from: PolicyTriggeredFrom;
  decision: PolicyDecisionType;
  severity: PolicySeverity;
  confidence: string | null;
  summary: string;
  rationale: string;
  matched_rules: PolicyMatchedRule[];
  recommendation: string;
  risk_decision: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type EvaluateTradePolicyPayload = {
  market_id: number;
  trade_type: string;
  side: string;
  quantity: string;
  requested_price?: string | null;
  triggered_from?: PolicyTriggeredFrom;
  requested_by?: PolicyRequestedBy;
  risk_assessment_id?: number | null;
  metadata?: Record<string, unknown>;
};

export type PolicyDecisionSummary = {
  total_decisions: number;
  auto_approve_count: number;
  approval_required_count: number;
  hard_block_count: number;
  latest_decision: TradePolicyEvaluation | null;
};

export type ApprovalFlowState = {
  riskReady: boolean;
  policyReady: boolean;
  canExecuteDirectly: boolean;
  requiresManualApproval: boolean;
  isBlocked: boolean;
};

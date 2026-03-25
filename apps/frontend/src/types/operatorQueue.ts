export type OperatorQueueStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'SNOOZED' | 'EXPIRED' | 'EXECUTED';
export type OperatorQueueSource = 'policy' | 'safety' | 'allocation' | 'semi_auto' | 'continuous_demo' | 'real_ops';
export type OperatorQueueType = 'approval_required' | 'escalation' | 'safety_review' | 'blocked_review';
export type OperatorQueuePriority = 'low' | 'medium' | 'high' | 'critical';

export type OperatorDecisionLog = {
  id: number;
  decision: 'APPROVE' | 'REJECT' | 'SNOOZE' | 'CANCEL' | 'FORCE_BLOCK';
  decided_by: string;
  decision_note: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type OperatorQueueItem = {
  id: number;
  status: OperatorQueueStatus;
  source: OperatorQueueSource;
  queue_type: OperatorQueueType;
  priority: OperatorQueuePriority;
  headline: string;
  summary: string;
  rationale: string;
  suggested_action: string;
  suggested_quantity: string | null;
  related_proposal: number | null;
  proposal_headline: string;
  related_market: number | null;
  market_title: string;
  market_source_type: string;
  is_real_data: boolean;
  related_pending_approval: number | null;
  related_trade: number | null;
  expires_at: string | null;
  snoozed_until: string | null;
  metadata: Record<string, unknown>;
  decision_logs: OperatorDecisionLog[];
  created_at: string;
  updated_at: string;
};

export type OperatorQueueSummary = {
  pending_count: number;
  high_priority_count: number;
  approvals_recent: number;
  rejected_recent: number;
  snoozed_count: number;
  paper_demo_only: boolean;
  real_execution_enabled: boolean;
  manual_operator_required_for_exceptions: boolean;
};

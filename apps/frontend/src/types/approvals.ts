export type ApprovalSourceType = 'runbook_checkpoint' | 'go_live_request' | 'operator_queue_item' | 'rollout_decision' | 'promotion_review' | 'other';
export type ApprovalStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'EXPIRED' | 'ESCALATED' | 'CANCELLED';
export type ApprovalPriority = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export type ApprovalImpactPreview = {
  approve: string;
  reject: string;
  expire: string;
  escalate: string;
  evidence: string[];
};

export type ApprovalDecision = {
  id: number;
  approval_request: number;
  decision: 'APPROVE' | 'REJECT' | 'EXPIRE' | 'ESCALATE';
  rationale: string;
  decided_by: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type ApprovalRequest = {
  id: number;
  source_type: ApprovalSourceType;
  source_object_id: string;
  title: string;
  summary: string;
  priority: ApprovalPriority;
  status: ApprovalStatus;
  requested_at: string;
  decided_at: string | null;
  expires_at: string | null;
  metadata: Record<string, unknown> & { impact_preview?: ApprovalImpactPreview; trace?: { root_type: string; root_id: string } };
  impact_preview: ApprovalImpactPreview;
  decisions: ApprovalDecision[];
  created_at: string;
  updated_at: string;
};

export type ApprovalSummary = {
  pending: number;
  approved: number;
  rejected: number;
  expired: number;
  escalated: number;
  cancelled: number;
  high_priority_pending: number;
  approved_recently: number;
  expired_or_escalated: number;
  top_high_priority: Array<{
    id: number;
    source_type: ApprovalSourceType;
    title: string;
    priority: ApprovalPriority;
    requested_at: string;
  }>;
};

export type ApprovalDecisionPayload = {
  rationale?: string;
  decided_by?: string;
  metadata?: Record<string, unknown>;
};

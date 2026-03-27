export type GoLiveGateStateCode =
  | 'PAPER_ONLY_LOCKED'
  | 'PRELIVE_REHEARSAL_READY'
  | 'MANUAL_APPROVAL_PENDING'
  | 'LIVE_DISABLED_BY_POLICY'
  | 'REMEDIATION_REQUIRED';

export type CapitalFirewallRule = {
  id: number;
  code: string;
  title: string;
  description: string;
  enabled: boolean;
  block_live_transition: boolean;
};

export type GoLiveState = {
  state: GoLiveGateStateCode;
  blockers: string[];
  firewall: {
    firewall_enabled: boolean;
    live_transition_allowed: boolean;
    blocked_by_firewall: boolean;
    blocking_rule_codes: string[];
    rules: CapitalFirewallRule[];
  };
  latest_checklist_run_id: number | null;
  latest_approval_request_id: number | null;
  paper_only: boolean;
};

export type GoLiveChecklistRun = {
  id: number;
  requested_by: string;
  context: string;
  checklist_version: string;
  passed: boolean;
  gate_state: GoLiveGateStateCode;
  passed_items: string[];
  failed_items: string[];
  blocking_reasons: string[];
  evidence: Record<string, unknown>;
  created_at: string;
};

export type GoLiveApprovalRequest = {
  id: number;
  requested_by: string;
  rationale: string;
  scope: string;
  requested_mode: string;
  status: 'DRAFT' | 'PENDING' | 'APPROVED' | 'REJECTED' | 'EXPIRED';
  blocking_reasons: string[];
  checklist_run: number | null;
  created_at: string;
};

export type GoLiveRehearsalRun = {
  id: number;
  intent: number;
  checklist_run: number | null;
  approval_request: number | null;
  gate_state: GoLiveGateStateCode;
  allowed_to_proceed_in_rehearsal: boolean;
  blocked_by_firewall: boolean;
  missing_approvals: string[];
  missing_preconditions: string[];
  blocked_reasons: string[];
  final_dry_run_disposition: string;
  dry_run_reference_id: number | null;
  created_at: string;
};

export type GoLiveSummary = {
  gate: GoLiveState;
  checklists: { total: number; passed: number; failed: number };
  approvals: { total: number; status_counts: Record<string, number> };
  rehearsals: { total: number; allowed_in_rehearsal: number; blocked_by_firewall: number };
};

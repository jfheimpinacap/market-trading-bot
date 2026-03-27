export type AutomationTrustTier = 'MANUAL_ONLY' | 'APPROVAL_REQUIRED' | 'SAFE_AUTOMATION' | 'AUTO_BLOCKED';
export type AutomationDecisionOutcome = 'ALLOWED' | 'APPROVAL_REQUIRED' | 'MANUAL_ONLY' | 'BLOCKED';

export type AutomationPolicyRule = {
  id: number;
  profile: number;
  action_type: string;
  source_context_type: string;
  trust_tier: AutomationTrustTier;
  conditions: Record<string, unknown>;
  rationale: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type AutomationPolicyProfile = {
  id: number;
  slug: string;
  name: string;
  description: string;
  is_active: boolean;
  is_default: boolean;
  recommendation_mode: boolean;
  allow_runbook_auto_advance: boolean;
  metadata: Record<string, unknown>;
  rules?: AutomationPolicyRule[];
  created_at: string;
  updated_at: string;
};

export type AutomationDecision = {
  id: number;
  profile: number | null;
  rule: number | null;
  action_type: string;
  source_context_type: string;
  runbook_instance_id: number | null;
  runbook_step_id: number | null;
  trust_tier: AutomationTrustTier;
  effective_trust_tier: AutomationTrustTier;
  outcome: AutomationDecisionOutcome;
  reason_codes: string[];
  rationale: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type AutomationActionLog = {
  id: number;
  decision: number;
  source_runbook_instance_id: number | null;
  source_runbook_step_id: number | null;
  action_name: string;
  execution_status: 'EXECUTED' | 'SKIPPED' | 'FAILED';
  result_summary: string;
  output_refs: Record<string, unknown>;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type AutomationPolicyCurrent = {
  profile: AutomationPolicyProfile;
  rules: AutomationPolicyRule[];
  guardrails: {
    runtime_status: string | null;
    runtime_mode: string | null;
    safety_status: string | null;
    certification_level: string | null;
    degraded_mode_state: string | null;
  };
};

export type AutomationPolicySummary = {
  active_profile: AutomationPolicyProfile;
  decision_counts: Record<string, number>;
  log_counts: Record<string, number>;
  recent_decisions: AutomationDecision[];
  recent_action_logs: AutomationActionLog[];
  auto_eligible_action_types: string[];
  blocked_action_types: string[];
};

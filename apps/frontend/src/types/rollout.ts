export type StackRolloutMode = 'SHADOW_ONLY' | 'CANARY' | 'STAGED';
export type StackRolloutRunStatus = 'RUNNING' | 'PAUSED' | 'COMPLETED' | 'ROLLED_BACK' | 'FAILED';
export type RolloutDecisionCode = 'CONTINUE_ROLLOUT' | 'PAUSE_ROLLOUT' | 'ROLLBACK_NOW' | 'COMPLETE_PROMOTION' | 'EXTEND_CANARY';

export type RolloutGuardrailEvent = {
  id: number;
  run: number;
  code: string;
  severity: string;
  reason: string;
  metric_value: string | null;
  threshold_value: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type RolloutDecision = {
  id: number;
  run: number;
  decision: RolloutDecisionCode;
  rationale: string;
  reason_codes: string[];
  recommendation_payload: Record<string, unknown>;
  actor: string;
  created_at: string;
  updated_at: string;
};

export type StackRolloutPlan = {
  id: number;
  champion_binding: { id: number; name: string; execution_profile: string };
  candidate_binding: { id: number; name: string; execution_profile: string };
  source_review_run: number | null;
  mode: StackRolloutMode;
  canary_percentage: number;
  sampling_rule: string;
  profile_scope: string;
  guardrails: Record<string, number | string>;
  summary: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type StackRolloutRun = {
  id: number;
  plan: StackRolloutPlan;
  status: StackRolloutRunStatus;
  current_phase: string;
  routed_opportunities_count: number;
  champion_count: number;
  challenger_count: number;
  canary_count: number;
  started_at: string;
  finished_at: string | null;
  summary: string;
  metadata: Record<string, unknown>;
  guardrail_events: RolloutGuardrailEvent[];
  decisions: RolloutDecision[];
  created_at: string;
  updated_at: string;
};

export type RolloutSummary = {
  current_run: StackRolloutRun | null;
  latest_run: StackRolloutRun | null;
  total_runs: number;
  running_count: number;
  rolled_back_count: number;
  last_updated_at: string;
};

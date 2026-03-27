export type RunbookInstanceStatus = 'OPEN' | 'IN_PROGRESS' | 'BLOCKED' | 'COMPLETED' | 'ABORTED' | 'ESCALATED';
export type RunbookStepStatus = 'PENDING' | 'READY' | 'RUNNING' | 'DONE' | 'FAILED' | 'SKIPPED';
export type RunbookStepActionKind = 'manual' | 'api_action' | 'review' | 'confirm';
export type RunbookAutopilotRunStatus = 'RUNNING' | 'PAUSED_FOR_APPROVAL' | 'BLOCKED' | 'COMPLETED' | 'FAILED' | 'ABORTED';
export type RunbookAutopilotStepOutcome = 'AUTO_EXECUTED' | 'APPROVAL_REQUIRED' | 'MANUAL_ONLY' | 'BLOCKED' | 'FAILED' | 'SKIPPED';
export type RunbookApprovalCheckpointStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'EXPIRED';

export type RunbookTemplate = {
  id: number;
  name: string;
  slug: string;
  trigger_type: string;
  description: string;
  severity_hint: string;
  is_enabled: boolean;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type RunbookActionResult = {
  id: number;
  runbook_step: number;
  action_name: string;
  action_status: 'STARTED' | 'SUCCESS' | 'FAILED' | 'SKIPPED';
  started_at: string;
  finished_at: string | null;
  result_summary: string;
  output_refs: Record<string, unknown>;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type RunbookStep = {
  id: number;
  runbook_instance: number;
  step_order: number;
  step_type: string;
  title: string;
  instructions: string;
  action_kind: RunbookStepActionKind;
  status: RunbookStepStatus;
  metadata: Record<string, unknown>;
  action_results: RunbookActionResult[];
  created_at: string;
  updated_at: string;
};

export type RunbookInstance = {
  id: number;
  template: RunbookTemplate;
  source_object_type: string;
  source_object_id: string;
  status: RunbookInstanceStatus;
  priority: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  summary: string;
  metadata: Record<string, unknown>;
  steps: RunbookStep[];
  created_at: string;
  updated_at: string;
};

export type RunbookAutopilotStepResult = {
  id: number;
  autopilot_run: number;
  runbook_step: RunbookStep;
  attempt: number;
  outcome: RunbookAutopilotStepOutcome;
  automation_decision_id: number | null;
  automation_action_log_id: number | null;
  runbook_action_result: number | null;
  rationale: string;
  error_message: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type RunbookApprovalCheckpoint = {
  id: number;
  autopilot_run: number;
  runbook_instance: number;
  runbook_step: number;
  approval_reason: string;
  blocking_constraints: string[];
  context_snapshot: Record<string, unknown>;
  status: RunbookApprovalCheckpointStatus;
  approved_at: string | null;
  resolved_by: string;
  created_at: string;
  updated_at: string;
};

export type RunbookAutopilotRun = {
  id: number;
  runbook_instance: number;
  status: RunbookAutopilotRunStatus;
  steps_evaluated: number;
  steps_auto_executed: number;
  steps_waiting_manual: number;
  steps_blocked: number;
  started_at: string;
  finished_at: string | null;
  summary: string;
  metadata: Record<string, unknown>;
  step_results: RunbookAutopilotStepResult[];
  approval_checkpoints: RunbookApprovalCheckpoint[];
  created_at: string;
  updated_at: string;
};

export type RunbookSummary = {
  counts: {
    open: number;
    in_progress: number;
    blocked: number;
    completed: number;
    escalated: number;
    aborted: number;
    total: number;
  };
  top_active: Array<{
    id: number;
    template_slug: string;
    priority: string;
    status: RunbookInstanceStatus;
    source_object_type: string;
    source_object_id: string;
    progress: { done: number; total: number };
    next_step: { id: number; title: string; status: RunbookStepStatus } | null;
    updated_at: string;
  }>;
};

export type RunbookAutopilotSummary = {
  counts: {
    running: number;
    paused_for_approval: number;
    blocked: number;
    completed: number;
    failed: number;
    aborted: number;
    total: number;
  };
  recent: Array<{
    id: number;
    runbook_instance_id: number;
    status: RunbookAutopilotRunStatus;
    summary: string;
    steps_evaluated: number;
    steps_auto_executed: number;
    steps_waiting_manual: number;
    steps_blocked: number;
    updated_at: string;
  }>;
};

export type RunbookRecommendation = {
  template_slug: string;
  reason: string;
  source_object_type: string;
  source_object_id: string;
  priority: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
};

export type CreateRunbookPayload = {
  template_slug: string;
  source_object_type: string;
  source_object_id: string;
  priority?: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  summary?: string;
  metadata?: Record<string, unknown>;
};

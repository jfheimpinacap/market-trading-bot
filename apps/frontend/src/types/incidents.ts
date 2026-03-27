export type IncidentSeverity = 'info' | 'warning' | 'high' | 'critical';
export type IncidentStatus = 'OPEN' | 'MITIGATING' | 'DEGRADED' | 'RECOVERING' | 'RESOLVED' | 'ESCALATED';

export type IncidentActionStatus = 'PLANNED' | 'APPLIED' | 'FAILED' | 'SKIPPED';
export type IncidentRecoveryStatus = 'STARTED' | 'SUCCESS' | 'FAILED' | 'SKIPPED';

export type IncidentAction = {
  id: number;
  incident: number;
  action_type: string;
  action_status: IncidentActionStatus;
  rationale: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type IncidentRecoveryRun = {
  id: number;
  incident: number;
  run_status: IncidentRecoveryStatus;
  trigger: string;
  summary: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type IncidentRecord = {
  id: number;
  incident_type: string;
  severity: IncidentSeverity;
  status: IncidentStatus;
  title: string;
  summary: string;
  source_app: string;
  related_object_type: string | null;
  related_object_id: string | null;
  first_seen_at: string;
  last_seen_at: string;
  dedupe_key: string | null;
  metadata: Record<string, unknown>;
  actions: IncidentAction[];
  recovery_runs: IncidentRecoveryRun[];
  created_at: string;
  updated_at: string;
};

export type DegradedModeState = {
  id: number;
  state: string;
  mission_control_paused: boolean;
  auto_execution_enabled: boolean;
  rollout_enabled: boolean;
  degraded_modules: string[];
  disabled_actions: string[];
  reasons: string[];
  activated_at: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type IncidentSummary = {
  active_incidents: number;
  critical_active: number;
  high_active: number;
  warning_active: number;
  resolved_total: number;
  by_type: Array<{ incident_type: string; count: number }>;
};

export type IncidentCurrentState = {
  degraded_mode: DegradedModeState;
  summary: IncidentSummary;
};

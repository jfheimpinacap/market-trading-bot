export type RuntimeMode = 'OBSERVE_ONLY' | 'PAPER_ASSIST' | 'PAPER_SEMI_AUTO' | 'PAPER_AUTO';
export type RuntimeStatus = 'ACTIVE' | 'DEGRADED' | 'PAUSED' | 'STOPPED';

export type RuntimeState = {
  id: number;
  current_mode: RuntimeMode;
  desired_mode: RuntimeMode | null;
  status: RuntimeStatus;
  set_by: string;
  rationale: string;
  effective_at: string;
  updated_at: string;
  metadata: Record<string, unknown>;
};

export type RuntimeStatusResponse = {
  state: RuntimeState;
  readiness_status: 'READY' | 'CAUTION' | 'NOT_READY' | null;
  safety_status: {
    status: string;
    status_message: string;
    kill_switch_enabled: boolean;
    hard_stop_active: boolean;
  };
  constraints: {
    allowed: boolean;
    reasons: string[];
  };
  global_operating_mode: GlobalOperatingMode;
  global_mode_influence: Record<string, string>;
};

export type RuntimeModeOption = {
  mode: RuntimeMode;
  label: string;
  description: string;
  is_allowed_now: boolean;
  blocked_reasons: string[];
  readiness_status: string | null;
  safety_status: string;
};

export type RuntimeTransition = {
  id: number;
  from_mode: RuntimeMode | null;
  to_mode: RuntimeMode;
  from_status: RuntimeStatus | null;
  to_status: RuntimeStatus;
  trigger_source: string;
  reason: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type RuntimeCapabilities = {
  mode: RuntimeMode;
  allow_signal_generation: boolean;
  allow_proposals: boolean;
  allow_allocation: boolean;
  allow_real_market_ops: boolean;
  allow_auto_execution: boolean;
  allow_continuous_loop: boolean;
  require_operator_for_all_trades: boolean;
  allow_pending_approvals: boolean;
  allow_replay: boolean;
  allow_experiments: boolean;
  max_auto_trades_per_cycle: number;
  max_auto_trades_per_session: number;
  blocked_reasons: string[];
};

export type SetRuntimeModePayload = {
  mode: RuntimeMode;
  rationale?: string;
  set_by?: string;
  metadata?: Record<string, unknown>;
};

export type GlobalOperatingMode = 'BALANCED' | 'CAUTION' | 'MONITOR_ONLY' | 'RECOVERY_MODE' | 'THROTTLED' | 'BLOCKED';

export type RuntimePostureRun = {
  id: number;
  started_at: string;
  completed_at: string | null;
  considered_signal_count: number;
  mode_kept_count: number;
  mode_switch_count: number;
  caution_count: number;
  monitor_only_count: number;
  recovery_mode_count: number;
  throttled_count: number;
  blocked_count: number;
  recommendation_summary: Record<string, unknown>;
  metadata: Record<string, unknown>;
};

export type RuntimePostureSnapshot = {
  id: number;
  exposure_pressure_state: string;
  admission_pressure_state: string;
  session_health_state: string;
  recent_loss_state: string;
  signal_quality_state: string;
  runtime_posture: string;
  safety_posture: string;
  incident_pressure_state: string;
  portfolio_pressure_state: string;
  snapshot_summary: string;
  reason_codes: string[];
  metadata: Record<string, unknown>;
  created_at_snapshot: string;
};

export type OperatingModeDecision = {
  id: number;
  current_mode: GlobalOperatingMode | null;
  target_mode: GlobalOperatingMode;
  decision_type: string;
  decision_status: string;
  auto_applicable: boolean;
  decision_summary: string;
  reason_codes: string[];
  metadata: Record<string, unknown>;
  created_at_decision: string;
};

export type OperatingModeSwitchRecord = {
  id: number;
  previous_mode: GlobalOperatingMode | null;
  applied_mode: GlobalOperatingMode;
  switch_status: string;
  switch_summary: string;
  metadata: Record<string, unknown>;
  created_at_switch: string;
};

export type OperatingModeRecommendation = {
  id: number;
  recommendation_type: string;
  rationale: string;
  reason_codes: string[];
  confidence: number;
  blockers: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type OperatingModeSummary = {
  latest_run_id: number | null;
  latest_decision_id: number | null;
  active_mode: GlobalOperatingMode;
  posture_reviews: number;
  mode_kept: number;
  mode_switched: number;
  caution_count: number;
  monitor_only_count: number;
  recovery_mode_count: number;
  throttled_count: number;
  blocked_count: number;
  recommendation_summary: Record<string, unknown>;
};

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

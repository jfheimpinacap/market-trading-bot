export type SafetySeverity = 'INFO' | 'WARNING' | 'CRITICAL';
export type SafetySystemStatus = 'HEALTHY' | 'WARNING' | 'COOLDOWN' | 'PAUSED' | 'HARD_STOP' | 'KILL_SWITCH';

export type SafetyEvent = {
  id: number;
  event_type: string;
  severity: SafetySeverity;
  source: string;
  related_session_id: number | null;
  related_cycle_id: number | null;
  related_market_id: number | null;
  related_trade_id: number | null;
  message: string;
  details: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type SafetyConfig = {
  id: number;
  name: string;
  status: SafetySystemStatus;
  status_message: string;
  max_auto_trades_per_cycle: number;
  max_auto_trades_per_session: number;
  max_position_value_per_market: string;
  max_total_open_exposure: string;
  max_daily_or_session_drawdown: string;
  max_unrealized_loss_threshold: string;
  cooldown_after_block_count: number;
  cooldown_cycles: number;
  hard_stop_after_error_count: number;
  require_manual_approval_above_quantity: string;
  require_manual_approval_above_exposure: string;
  kill_switch_enabled: boolean;
  cooldown_until_cycle: number | null;
  hard_stop_active: boolean;
  paused_by_safety: boolean;
};

export type SafetyStatus = {
  status: SafetySystemStatus;
  status_message: string;
  kill_switch_enabled: boolean;
  hard_stop_active: boolean;
  cooldown_until_cycle: number | null;
  paused_by_safety: boolean;
  account_snapshot: Record<string, string> | null;
  limits: Record<string, string | number>;
  counters: Record<string, number>;
  last_event: {
    id: number;
    event_type: string;
    severity: SafetySeverity;
    source: string;
    message: string;
    created_at: string;
  } | null;
};

export type SafetySummary = {
  status: SafetyStatus;
  recent_events: SafetyEvent[];
};

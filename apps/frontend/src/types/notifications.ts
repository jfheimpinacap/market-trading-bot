export type NotificationChannelType = 'ui_only' | 'email' | 'webhook' | 'telegram' | 'discord' | 'slack';
export type NotificationDeliveryMode = 'immediate' | 'digest' | 'escalation' | 'escalation_only';
export type NotificationDeliveryStatus = 'PENDING' | 'SENT' | 'FAILED' | 'SKIPPED' | 'SUPPRESSED';
export type NotificationTriggerSource = 'manual' | 'automatic' | 'digest_automation' | 'escalation';

export type NotificationChannel = {
  id: number;
  name: string;
  slug: string;
  channel_type: NotificationChannelType;
  is_enabled: boolean;
  config: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type NotificationRule = {
  id: number;
  name: string;
  is_enabled: boolean;
  match_criteria: Record<string, unknown>;
  delivery_mode: NotificationDeliveryMode;
  channel_refs: number[];
  severity_threshold: 'info' | 'warning' | 'high' | 'critical';
  cooldown_seconds: number;
  dedupe_window_seconds: number;
  created_at: string;
  updated_at: string;
};

export type NotificationDelivery = {
  id: number;
  related_alert: number | null;
  related_digest: number | null;
  channel: number | null;
  channel_slug: string | null;
  channel_type: NotificationChannelType | null;
  delivery_status: NotificationDeliveryStatus;
  delivery_mode: NotificationDeliveryMode;
  trigger_source: NotificationTriggerSource;
  reason: string;
  payload_preview: Record<string, unknown>;
  response_metadata: Record<string, unknown>;
  created_at: string;
  delivered_at: string | null;
};

export type NotificationAutomationState = {
  id: number;
  is_enabled: boolean;
  automatic_dispatch_enabled: boolean;
  automatic_digest_enabled: boolean;
  escalation_enabled: boolean;
  suppress_info_alerts_by_default: boolean;
  digest_interval_minutes: number;
  escalation_after_minutes: number;
  max_auto_notifications_per_window: number;
  automation_window_minutes: number;
  last_automatic_dispatch_at: string | null;
  last_digest_cycle_at: string | null;
  last_escalation_cycle_at: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type NotificationEscalationEvent = {
  id: number;
  alert: number;
  alert_source: string;
  alert_title: string;
  severity: string;
  reason: string;
  status: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type NotificationSummary = {
  channels_enabled: number;
  rules_enabled: number;
  deliveries_total: number;
  deliveries_sent: number;
  deliveries_failed: number;
  deliveries_pending: number;
  deliveries_suppressed: number;
  delivery_health: 'healthy' | 'attention';
  by_channel: Array<{ channel__slug: string | null; channel__channel_type: string | null; count: number }>;
};

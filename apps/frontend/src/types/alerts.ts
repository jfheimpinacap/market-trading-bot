export type AlertType = 'approval_required' | 'safety' | 'runtime' | 'sync' | 'readiness' | 'queue' | 'portfolio' | 'anomaly';
export type AlertSeverity = 'info' | 'warning' | 'high' | 'critical';
export type AlertStatus = 'OPEN' | 'ACKNOWLEDGED' | 'RESOLVED' | 'SUPPRESSED';

export type OperatorAlert = {
  id: number;
  alert_type: AlertType;
  severity: AlertSeverity;
  status: AlertStatus;
  title: string;
  summary: string;
  source: string;
  related_object_type: string | null;
  related_object_id: string | null;
  dedupe_key: string | null;
  first_seen_at: string;
  last_seen_at: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  latest_notification_status?: 'PENDING' | 'SENT' | 'FAILED' | 'SKIPPED' | 'SUPPRESSED' | null;
  latest_notification_channel?: string | null;
};

export type OperatorAlertsSummary = {
  open_alerts: number;
  critical_alerts: number;
  warning_alerts: number;
  high_alerts: number;
  pending_approvals_attention: number;
  stale_provider_issues: number;
  by_source: Array<{ source: string; count: number }>;
};

export type OperatorDigest = {
  id: number;
  digest_type: 'daily' | 'session' | 'manual' | 'cycle_window';
  window_start: string;
  window_end: string;
  summary: string;
  alerts_count: number;
  critical_count: number;
  approvals_pending_count: number;
  safety_events_count: number;
  runtime_changes_count: number;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  latest_notification_status?: 'PENDING' | 'SENT' | 'FAILED' | 'SKIPPED' | 'SUPPRESSED' | null;
  latest_notification_channel?: string | null;
};

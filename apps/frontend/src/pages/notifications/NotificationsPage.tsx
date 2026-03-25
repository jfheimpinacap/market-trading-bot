import { useCallback, useEffect, useState } from 'react';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { EmptyState } from '../../components/EmptyState';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import {
  disableNotificationAutomation,
  enableNotificationAutomation,
  getNotificationAutomationStatus,
  getNotificationChannels,
  getNotificationDeliveries,
  getNotificationEscalations,
  getNotificationRules,
  getNotificationSummary,
  runAutomaticDispatch,
  runDigestCycle,
  sendAlertNotification,
  sendDigestNotification,
} from '../../services/notifications';
import { getAlertDigests, getAlerts } from '../../services/alerts';
import type { OperatorAlert, OperatorDigest } from '../../types/alerts';
import type {
  NotificationAutomationState,
  NotificationChannel,
  NotificationDelivery,
  NotificationEscalationEvent,
  NotificationRule,
  NotificationSummary,
} from '../../types/notifications';

function formatDate(value: string | null) {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short' }).format(date);
}

function statusTone(status: string) {
  if (status === 'SENT') return 'ready';
  if (status === 'FAILED') return 'offline';
  if (status === 'SUPPRESSED') return 'pending';
  return 'neutral';
}

function modeTone(mode: string) {
  if (mode === 'immediate') return 'ready';
  if (mode === 'digest') return 'pending';
  if (mode === 'escalation') return 'offline';
  return 'neutral';
}

function triggerTone(trigger: string) {
  if (trigger === 'automatic' || trigger === 'digest_automation') return 'pending';
  if (trigger === 'escalation') return 'offline';
  return 'neutral';
}

export function NotificationsPage() {
  const [summary, setSummary] = useState<NotificationSummary | null>(null);
  const [automation, setAutomation] = useState<NotificationAutomationState | null>(null);
  const [channels, setChannels] = useState<NotificationChannel[]>([]);
  const [rules, setRules] = useState<NotificationRule[]>([]);
  const [deliveries, setDeliveries] = useState<NotificationDelivery[]>([]);
  const [escalations, setEscalations] = useState<NotificationEscalationEvent[]>([]);
  const [alerts, setAlerts] = useState<OperatorAlert[]>([]);
  const [digests, setDigests] = useState<OperatorDigest[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isActionLoading, setIsActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [summaryResponse, automationResponse, channelsResponse, rulesResponse, deliveriesResponse, alertsResponse, digestsResponse, escalationsResponse] = await Promise.all([
        getNotificationSummary(),
        getNotificationAutomationStatus(),
        getNotificationChannels(),
        getNotificationRules(),
        getNotificationDeliveries(),
        getAlerts({ status: 'OPEN' }),
        getAlertDigests(),
        getNotificationEscalations(),
      ]);
      setSummary(summaryResponse);
      setAutomation(automationResponse);
      setChannels(channelsResponse);
      setRules(rulesResponse);
      setDeliveries(deliveriesResponse);
      setAlerts(alertsResponse);
      setDigests(digestsResponse);
      setEscalations(escalationsResponse);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load notification center.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function sendLatestAlert() {
    if (!alerts[0]) return;
    setIsActionLoading(true);
    try {
      await sendAlertNotification(alerts[0].id);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not send alert notification.');
    } finally {
      setIsActionLoading(false);
    }
  }

  async function sendLatestDigest() {
    if (!digests[0]) return;
    setIsActionLoading(true);
    try {
      await sendDigestNotification(digests[0].id);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not send digest notification.');
    } finally {
      setIsActionLoading(false);
    }
  }

  async function toggleAutomation(enabled: boolean) {
    setIsActionLoading(true);
    try {
      if (enabled) {
        await enableNotificationAutomation();
      } else {
        await disableNotificationAutomation();
      }
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not change automation status.');
    } finally {
      setIsActionLoading(false);
    }
  }

  async function runAutoDispatchNow() {
    setIsActionLoading(true);
    try {
      await runAutomaticDispatch();
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not run automatic dispatch.');
    } finally {
      setIsActionLoading(false);
    }
  }

  async function runDigestNow() {
    setIsActionLoading(true);
    try {
      await runDigestCycle(true);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not run digest cycle.');
    } finally {
      setIsActionLoading(false);
    }
  }

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Operator notifications"
        title="Notification Delivery & Escalation Routing"
        description="Delivery layer for paper/demo operator alerts, now with automatic dispatch, digest cadence, and escalation traceability."
        actions={<div className="button-row"><button type="button" className="secondary-button" disabled={isActionLoading || alerts.length === 0} onClick={() => void sendLatestAlert()}>Send latest open alert</button><button type="button" className="secondary-button" disabled={isActionLoading || digests.length === 0} onClick={() => void sendLatestDigest()}>Send latest digest</button></div>}
      />

      <DataStateWrapper isLoading={isLoading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <div className="dashboard-stats-grid">
          <article className="stat-card"><p className="section-label">Channels enabled</p><h3>{summary?.channels_enabled ?? 0}</h3></article>
          <article className="stat-card"><p className="section-label">Rules enabled</p><h3>{summary?.rules_enabled ?? 0}</h3></article>
          <article className="stat-card"><p className="section-label">Deliveries sent</p><h3>{summary?.deliveries_sent ?? 0}</h3></article>
          <article className="stat-card"><p className="section-label">Failed</p><h3>{summary?.deliveries_failed ?? 0}</h3></article>
          <article className="stat-card"><p className="section-label">Suppressed</p><h3>{summary?.deliveries_suppressed ?? 0}</h3></article>
        </div>

        <SectionCard eyebrow="Automation" title="Automation status" description="Automatic dispatch, digest cycle, and escalation controls for local-first paper/demo operations.">
          {automation ? (
            <div className="table-wrapper"><table className="data-table"><thead><tr><th>Global</th><th>Immediate dispatch</th><th>Digest automation</th><th>Escalation</th><th>Last auto dispatch</th><th>Last digest</th><th>Last escalation</th></tr></thead><tbody>
              <tr>
                <td><StatusBadge tone={automation.is_enabled ? 'ready' : 'offline'}>{automation.is_enabled ? 'ENABLED' : 'DISABLED'}</StatusBadge></td>
                <td>{automation.automatic_dispatch_enabled ? 'Yes' : 'No'}</td>
                <td>{automation.automatic_digest_enabled ? 'Yes' : 'No'}</td>
                <td>{automation.escalation_enabled ? 'Yes' : 'No'}</td>
                <td>{formatDate(automation.last_automatic_dispatch_at)}</td>
                <td>{formatDate(automation.last_digest_cycle_at)}</td>
                <td>{formatDate(automation.last_escalation_cycle_at)}</td>
              </tr>
            </tbody></table></div>
          ) : <EmptyState eyebrow="Automation" title="Automation state unavailable" description="Could not load automation settings." />}
          <div className="button-row" style={{ marginTop: '1rem' }}>
            <button type="button" className="secondary-button" disabled={isActionLoading || Boolean(automation?.is_enabled)} onClick={() => void toggleAutomation(true)}>Enable automation</button>
            <button type="button" className="secondary-button" disabled={isActionLoading || !automation?.is_enabled} onClick={() => void toggleAutomation(false)}>Disable automation</button>
            <button type="button" className="secondary-button" disabled={isActionLoading || !automation?.is_enabled} onClick={() => void runAutoDispatchNow()}>Run automatic dispatch now</button>
            <button type="button" className="secondary-button" disabled={isActionLoading || !automation?.is_enabled} onClick={() => void runDigestNow()}>Run digest cycle now</button>
          </div>
          {!automation?.is_enabled ? <p className="section-label" style={{ marginTop: '0.75rem' }}>Automatic notification delivery is currently disabled.</p> : null}
        </SectionCard>

        <SectionCard eyebrow="History" title="Recent deliveries" description="Traceability by mode, trigger source, status and reason.">
          {deliveries.length === 0 ? (
            <EmptyState eyebrow="Delivery" title="No deliveries yet" description="No manual or automatic sends were recorded yet." />
          ) : (
            <div className="table-wrapper"><table className="data-table"><thead><tr><th>Status</th><th>Mode</th><th>Trigger</th><th>Channel</th><th>Alert</th><th>Digest</th><th>Reason</th><th>Created</th><th>Delivered</th></tr></thead><tbody>
              {deliveries.slice(0, 100).map((item) => <tr key={item.id}><td><StatusBadge tone={statusTone(item.delivery_status)}>{item.delivery_status}</StatusBadge></td><td><StatusBadge tone={modeTone(item.delivery_mode)}>{item.delivery_mode.toUpperCase()}</StatusBadge></td><td><StatusBadge tone={triggerTone(item.trigger_source)}>{item.trigger_source.toUpperCase()}</StatusBadge></td><td>{item.channel_slug ?? '—'}</td><td>{item.related_alert ?? '—'}</td><td>{item.related_digest ?? '—'}</td><td>{item.reason}</td><td>{formatDate(item.created_at)}</td><td>{formatDate(item.delivered_at)}</td></tr>)}
            </tbody></table></div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Escalation" title="Recent escalations" description="Persistent or critical incidents elevated automatically.">
          {escalations.length === 0 ? (
            <EmptyState eyebrow="Escalations" title="No escalations triggered recently" description="No persistent incidents needed escalation in the latest cycles." />
          ) : (
            <div className="table-wrapper"><table className="data-table"><thead><tr><th>Alert</th><th>Source</th><th>Severity</th><th>Reason</th><th>Status</th><th>Created</th></tr></thead><tbody>
              {escalations.map((item) => <tr key={item.id}><td>{item.alert_title}</td><td>{item.alert_source}</td><td>{item.severity}</td><td>{item.reason}</td><td><StatusBadge tone={item.status === 'TRIGGERED' ? 'offline' : 'neutral'}>{item.status}</StatusBadge></td><td>{formatDate(item.created_at)}</td></tr>)}
            </tbody></table></div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Rules" title="Routing rules" description="Explicit matching + minimum severity + cooldown/dedupe windows.">
          {rules.length === 0 ? <EmptyState eyebrow="Rules" title="No routing rules yet" description="Create immediate/digest/escalation rules through the API." /> : (
            <div className="table-wrapper"><table className="data-table"><thead><tr><th>Name</th><th>Mode</th><th>Severity min</th><th>Cooldown</th><th>Dedupe</th><th>Channels</th><th>Enabled</th></tr></thead><tbody>
              {rules.map((rule) => <tr key={rule.id}><td>{rule.name}</td><td><StatusBadge tone={modeTone(rule.delivery_mode)}>{rule.delivery_mode.toUpperCase()}</StatusBadge></td><td>{rule.severity_threshold}</td><td>{rule.cooldown_seconds}s</td><td>{rule.dedupe_window_seconds}s</td><td>{rule.channel_refs.join(', ') || 'auto ui_only'}</td><td>{rule.is_enabled ? 'Yes' : 'No'}</td></tr>)}
            </tbody></table></div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Channels" title="Configured delivery channels" description="Initial scope: UI-only + simple webhook/email hooks.">
          {channels.length === 0 ? (
            <EmptyState eyebrow="Channels" title="No channels configured" description="UI-only channel is auto-created when summary/channels are loaded." />
          ) : (
            <div className="table-wrapper"><table className="data-table"><thead><tr><th>Name</th><th>Slug</th><th>Type</th><th>Enabled</th><th>Config</th></tr></thead><tbody>
              {channels.map((channel) => <tr key={channel.id}><td>{channel.name}</td><td>{channel.slug}</td><td>{channel.channel_type}</td><td>{channel.is_enabled ? 'Yes' : 'No'}</td><td><pre>{JSON.stringify(channel.config ?? {}, null, 2)}</pre></td></tr>)}
            </tbody></table></div>
          )}
        </SectionCard>
      </DataStateWrapper>
    </div>
  );
}

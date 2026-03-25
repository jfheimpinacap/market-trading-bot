import { useCallback, useEffect, useState } from 'react';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { EmptyState } from '../../components/EmptyState';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { getAlertDigests, getAlerts } from '../../services/alerts';
import { getNotificationChannels, getNotificationDeliveries, getNotificationRules, getNotificationSummary, sendAlertNotification, sendDigestNotification } from '../../services/notifications';
import type { OperatorAlert, OperatorDigest } from '../../types/alerts';
import type { NotificationChannel, NotificationDelivery, NotificationRule, NotificationSummary } from '../../types/notifications';

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
  return 'neutral';
}

export function NotificationsPage() {
  const [summary, setSummary] = useState<NotificationSummary | null>(null);
  const [channels, setChannels] = useState<NotificationChannel[]>([]);
  const [rules, setRules] = useState<NotificationRule[]>([]);
  const [deliveries, setDeliveries] = useState<NotificationDelivery[]>([]);
  const [alerts, setAlerts] = useState<OperatorAlert[]>([]);
  const [digests, setDigests] = useState<OperatorDigest[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isActionLoading, setIsActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [summaryResponse, channelsResponse, rulesResponse, deliveriesResponse, alertsResponse, digestsResponse] = await Promise.all([
        getNotificationSummary(),
        getNotificationChannels(),
        getNotificationRules(),
        getNotificationDeliveries(),
        getAlerts({ status: 'OPEN' }),
        getAlertDigests(),
      ]);
      setSummary(summaryResponse);
      setChannels(channelsResponse);
      setRules(rulesResponse);
      setDeliveries(deliveriesResponse);
      setAlerts(alertsResponse);
      setDigests(digestsResponse);
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

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Operator notifications"
        title="Notification Delivery & Escalation Routing"
        description="Delivery layer for paper/demo operator alerts. This route decides what leaves the panel, through which channel, and why each delivery was sent or suppressed."
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

        <SectionCard eyebrow="Channels" title="Configured delivery channels" description="Initial scope: UI-only + simple webhook/email hooks.">
          {channels.length === 0 ? (
            <EmptyState eyebrow="Channels" title="No channels configured" description="UI-only channel is auto-created when summary/channels are loaded." />
          ) : (
            <div className="table-wrapper"><table className="data-table"><thead><tr><th>Name</th><th>Slug</th><th>Type</th><th>Enabled</th><th>Config</th></tr></thead><tbody>
              {channels.map((channel) => <tr key={channel.id}><td>{channel.name}</td><td>{channel.slug}</td><td>{channel.channel_type}</td><td>{channel.is_enabled ? 'Yes' : 'No'}</td><td><pre>{JSON.stringify(channel.config ?? {}, null, 2)}</pre></td></tr>)}
            </tbody></table></div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Rules" title="Routing rules" description="Explicit matching + minimum severity + cooldown/dedupe windows.">
          {rules.length === 0 ? <EmptyState eyebrow="Rules" title="No routing rules yet" description="Create at least one immediate and one digest rule through the API." /> : (
            <div className="table-wrapper"><table className="data-table"><thead><tr><th>Name</th><th>Mode</th><th>Severity min</th><th>Cooldown</th><th>Dedupe</th><th>Channels</th><th>Enabled</th></tr></thead><tbody>
              {rules.map((rule) => <tr key={rule.id}><td>{rule.name}</td><td><StatusBadge tone={modeTone(rule.delivery_mode)}>{rule.delivery_mode.toUpperCase()}</StatusBadge></td><td>{rule.severity_threshold}</td><td>{rule.cooldown_seconds}s</td><td>{rule.dedupe_window_seconds}s</td><td>{rule.channel_refs.join(', ') || 'auto ui_only'}</td><td>{rule.is_enabled ? 'Yes' : 'No'}</td></tr>)}
            </tbody></table></div>
          )}
        </SectionCard>

        <SectionCard eyebrow="History" title="Delivery history" description="Full traceability by channel, mode, status and reason.">
          {deliveries.length === 0 ? (
            <EmptyState eyebrow="Delivery" title="No deliveries yet" description="Good signal: no outbound sends were needed yet. Trigger a manual alert/digest send to validate routing." />
          ) : (
            <div className="table-wrapper"><table className="data-table"><thead><tr><th>Status</th><th>Mode</th><th>Channel</th><th>Alert</th><th>Digest</th><th>Reason</th><th>Created</th><th>Delivered</th></tr></thead><tbody>
              {deliveries.slice(0, 80).map((item) => <tr key={item.id}><td><StatusBadge tone={statusTone(item.delivery_status)}>{item.delivery_status}</StatusBadge></td><td><StatusBadge tone={modeTone(item.delivery_mode)}>{item.delivery_mode.toUpperCase()}</StatusBadge></td><td>{item.channel_slug ?? '—'}</td><td>{item.related_alert ?? '—'}</td><td>{item.related_digest ?? '—'}</td><td>{item.reason}</td><td>{formatDate(item.created_at)}</td><td>{formatDate(item.delivered_at)}</td></tr>)}
            </tbody></table></div>
          )}
        </SectionCard>
      </DataStateWrapper>
    </div>
  );
}

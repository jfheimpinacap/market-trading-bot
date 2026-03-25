import { useCallback, useEffect, useMemo, useState } from 'react';
import { navigate } from '../../lib/router';
import { EmptyState } from '../../components/EmptyState';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { acknowledgeAlert, getAlertDigests, getAlerts, getAlertsSummary, resolveAlert } from '../../services/alerts';
import type { OperatorAlert, OperatorAlertsSummary, OperatorDigest } from '../../types/alerts';

function toneFromSeverity(severity: string) {
  if (severity === 'critical') return 'offline';
  if (severity === 'high' || severity === 'warning') return 'pending';
  return 'neutral';
}

function toneFromStatus(status: string) {
  if (status === 'OPEN') return 'offline';
  if (status === 'ACKNOWLEDGED') return 'pending';
  if (status === 'RESOLVED') return 'ready';
  return 'neutral';
}

function formatDate(value: string | null) {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short' }).format(date);
}

export function AlertsPage() {
  const [alerts, setAlerts] = useState<OperatorAlert[]>([]);
  const [summary, setSummary] = useState<OperatorAlertsSummary | null>(null);
  const [digests, setDigests] = useState<OperatorDigest[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isActionLoading, setIsActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [alertsResponse, summaryResponse, digestResponse] = await Promise.all([
        getAlerts({ status: 'OPEN' }),
        getAlertsSummary(),
        getAlertDigests(),
      ]);
      setAlerts(alertsResponse);
      setSummary(summaryResponse);
      setDigests(digestResponse.slice(0, 5));
      if (!selectedId && alertsResponse.length > 0) setSelectedId(alertsResponse[0].id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load operator alerts.');
    } finally {
      setIsLoading(false);
    }
  }, [selectedId]);

  useEffect(() => {
    void load();
  }, [load]);

  const selected = useMemo(() => alerts.find((item) => item.id === selectedId) ?? null, [alerts, selectedId]);

  async function runAction(action: 'ack' | 'resolve') {
    if (!selected) return;
    setIsActionLoading(true);
    try {
      if (action === 'ack') {
        await acknowledgeAlert(selected.id);
      } else {
        await resolveAlert(selected.id);
      }
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not update alert status.');
    } finally {
      setIsActionLoading(false);
    }
  }

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Operator incident center"
        title="Operator Alerts"
        description="Operational alerts + digest pipeline for local paper/demo runtime. This center surfaces only meaningful exceptions that may need human intervention."
        actions={<div className="button-row"><button type="button" className="secondary-button" onClick={() => navigate('/operator-queue')}>Open Queue</button><button type="button" className="secondary-button" onClick={() => navigate('/runtime')}>Open Runtime</button></div>}
      />

      <DataStateWrapper isLoading={isLoading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <div className="dashboard-stats-grid">
          <article className="stat-card"><p className="section-label">Open alerts</p><h3>{summary?.open_alerts ?? 0}</h3></article>
          <article className="stat-card"><p className="section-label">Critical</p><h3>{summary?.critical_alerts ?? 0}</h3></article>
          <article className="stat-card"><p className="section-label">Warnings</p><h3>{summary?.warning_alerts ?? 0}</h3></article>
          <article className="stat-card"><p className="section-label">Pending approvals</p><h3>{summary?.pending_approvals_attention ?? 0}</h3></article>
          <article className="stat-card"><p className="section-label">Stale sync issues</p><h3>{summary?.stale_provider_issues ?? 0}</h3></article>
        </div>

        <SectionCard eyebrow="Attention queue" title="Open alerts" description="Consolidated operational exceptions from runtime, safety, queue, sync, readiness and continuous demo.">
          {alerts.length === 0 ? (
            <EmptyState title="No critical operator attention required right now." description="The alert layer is currently clear. Keep monitoring digests for context over time." eyebrow="All clear" />
          ) : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Severity</th><th>Type</th><th>Title</th><th>Summary</th><th>Source</th><th>First seen</th><th>Last seen</th><th>Status</th></tr></thead>
                <tbody>
                  {alerts.map((item) => (
                    <tr key={item.id} onClick={() => setSelectedId(item.id)} style={{ cursor: 'pointer' }}>
                      <td><StatusBadge tone={toneFromSeverity(item.severity)}>{item.severity.toUpperCase()}</StatusBadge></td>
                      <td>{item.alert_type}</td>
                      <td>{item.title}</td>
                      <td>{item.summary}</td>
                      <td>{item.source}</td>
                      <td>{formatDate(item.first_seen_at)}</td>
                      <td>{formatDate(item.last_seen_at)}</td>
                      <td><StatusBadge tone={toneFromStatus(item.status)}>{item.status}</StatusBadge></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Alert detail" title={selected ? `Alert #${selected.id}` : 'Select an alert'} description="Why this matters + suggested operator response.">
          {!selected ? (
            <EmptyState title="Select an alert" description="Pick a row to inspect metadata, related context, and operator actions." eyebrow="Detail" />
          ) : (
            <div className="page-stack">
              <p><strong>Why this matters:</strong> {selected.summary || 'Operational condition may require intervention.'}</p>
              <p><strong>Suggested action:</strong> Validate source module, confirm risk/safety posture, then acknowledge or resolve once mitigated.</p>
              <p><strong>Related object:</strong> {selected.related_object_type ?? '—'} / {selected.related_object_id ?? '—'}</p>
              <p><strong>Dedupe key:</strong> {selected.dedupe_key ?? '—'}</p>
              <div><strong>Metadata:</strong><pre>{JSON.stringify(selected.metadata ?? {}, null, 2)}</pre></div>
              <div className="button-row">
                <button type="button" className="secondary-button" disabled={isActionLoading} onClick={() => void runAction('ack')}>Acknowledge</button>
                <button type="button" className="primary-button" disabled={isActionLoading} onClick={() => void runAction('resolve')}>Resolve</button>
              </div>
            </div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Digest" title="Recent digests" description="What happened in recent windows without opening multiple pages.">
          {digests.length === 0 ? (
            <p>No digests generated yet. Use POST /api/alerts/build-digest/ to create one on demand.</p>
          ) : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Type</th><th>Window</th><th>Summary</th><th>Alerts</th><th>Critical</th><th>Approvals</th><th>Safety</th><th>Runtime</th></tr></thead>
                <tbody>
                  {digests.map((digest) => (
                    <tr key={digest.id}>
                      <td>{digest.digest_type}</td>
                      <td>{formatDate(digest.window_start)} → {formatDate(digest.window_end)}</td>
                      <td>{digest.summary}</td>
                      <td>{digest.alerts_count}</td>
                      <td>{digest.critical_count}</td>
                      <td>{digest.approvals_pending_count}</td>
                      <td>{digest.safety_events_count}</td>
                      <td>{digest.runtime_changes_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>
      </DataStateWrapper>
    </div>
  );
}

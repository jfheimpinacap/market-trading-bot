import { useCallback, useEffect, useMemo, useState } from 'react';

import { EmptyState } from '../../components/EmptyState';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { navigate } from '../../lib/router';
import { getIncidentCurrentState, getIncidents, getIncidentSummary, mitigateIncident, resolveIncident, runIncidentDetection } from '../../services/incidents';
import type { IncidentCurrentState, IncidentRecord, IncidentSummary } from '../../types/incidents';

function formatDate(value: string | null) {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short' }).format(date);
}

function severityTone(value: string) {
  if (value === 'critical') return 'offline';
  if (value === 'high' || value === 'warning') return 'pending';
  return 'neutral';
}

function statusTone(value: string) {
  if (value === 'OPEN' || value === 'ESCALATED') return 'offline';
  if (value === 'MITIGATING' || value === 'DEGRADED' || value === 'RECOVERING') return 'pending';
  if (value === 'RESOLVED') return 'ready';
  return 'neutral';
}

export function IncidentsPage() {
  const [incidents, setIncidents] = useState<IncidentRecord[]>([]);
  const [state, setState] = useState<IncidentCurrentState | null>(null);
  const [summary, setSummary] = useState<IncidentSummary | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [incidentsResponse, stateResponse, summaryResponse] = await Promise.all([
        getIncidents(),
        getIncidentCurrentState(),
        getIncidentSummary(),
      ]);
      setIncidents(incidentsResponse);
      setState(stateResponse);
      setSummary(summaryResponse);
      if (!selectedId && incidentsResponse.length > 0) setSelectedId(incidentsResponse[0].id);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load incidents state.');
    } finally {
      setLoading(false);
    }
  }, [selectedId]);

  useEffect(() => {
    void load();
  }, [load]);

  const selected = useMemo(() => incidents.find((item) => item.id === selectedId) ?? null, [incidents, selectedId]);

  const runAction = useCallback(async (action: () => Promise<unknown>, okMessage: string) => {
    setActionLoading(true);
    setMessage(null);
    setError(null);
    try {
      await action();
      setMessage(okMessage);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Incident action failed.');
    } finally {
      setActionLoading(false);
    }
  }, [load]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Incident commander"
        title="/incidents"
        description="Operational incident commander + self-healing orchestration for local-first paper/demo runtime. Conservative, auditable, and non-opaque by design."
        actions={<div className="button-row"><button type="button" className="secondary-button" onClick={() => navigate('/mission-control')}>Open Mission Control</button><button type="button" className="secondary-button" onClick={() => navigate('/runtime')}>Open Runtime</button><button type="button" className="secondary-button" onClick={() => navigate('/rollout')}>Open Rollout</button><button type="button" className="secondary-button" onClick={() => navigate('/alerts')}>Open Alerts</button><button type="button" className="secondary-button" onClick={() => navigate('/chaos')}>Open Chaos Lab</button><button type="button" className="secondary-button" onClick={() => navigate('/trace')}>Open Trace Explorer</button><button type="button" className="secondary-button" onClick={() => navigate('/runbooks')}>Open Runbooks</button></div>}
      />

      <SectionCard eyebrow="Controls" title="Detection + resolution controls" description="Run conservative detection, mitigate selected incidents, or mark resolved when conditions are restored.">
        <div className="button-row">
          <button type="button" className="secondary-button" disabled={actionLoading} onClick={() => void runAction(() => runIncidentDetection(), 'Detection run completed.')}>Run detection</button>
          <button type="button" className="secondary-button" disabled={actionLoading || !selected} onClick={() => selected && runAction(() => mitigateIncident(selected.id), `Incident #${selected.id} mitigation applied.`)}>Mitigate selected</button>
          <button type="button" className="primary-button" disabled={actionLoading || !selected} onClick={() => selected && runAction(() => resolveIncident(selected.id), `Incident #${selected.id} resolved.`)}>Resolve selected</button>
        </div>
        {message ? <p>{message}</p> : null}
      </SectionCard>

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Current degraded mode" title="System resilience state" description="What is degraded now, what is disabled, and why.">
          <div className="system-metadata-grid">
            <div><strong>State:</strong> <StatusBadge tone={statusTone(state?.degraded_mode.state?.toUpperCase() ?? 'NORMAL')}>{state?.degraded_mode.state ?? 'normal'}</StatusBadge></div>
            <div><strong>Mission control paused:</strong> {state?.degraded_mode.mission_control_paused ? 'Yes' : 'No'}</div>
            <div><strong>Auto execution:</strong> {state?.degraded_mode.auto_execution_enabled ? 'Enabled' : 'Disabled'}</div>
            <div><strong>Rollout:</strong> {state?.degraded_mode.rollout_enabled ? 'Enabled' : 'Disabled'}</div>
            <div><strong>Active incidents:</strong> {summary?.active_incidents ?? 0}</div>
            <div><strong>Critical active:</strong> {summary?.critical_active ?? 0}</div>
            <div><strong>Degraded modules:</strong> {(state?.degraded_mode.degraded_modules ?? []).join(', ') || 'None'}</div>
            <div><strong>Disabled actions:</strong> {(state?.degraded_mode.disabled_actions ?? []).join(', ') || 'None'}</div>
          </div>
          <p><strong>Reasons:</strong> {(state?.degraded_mode.reasons ?? []).slice(-3).join(' | ') || 'No active degraded reasons.'}</p>
        </SectionCard>

        <SectionCard eyebrow="Incident registry" title="Incident table" description="Operational incidents with severity, status, source, and traceability.">
          {incidents.length === 0 ? (
            <EmptyState eyebrow="Incidents" title="No incidents found" description="No active incidents detected right now." />
          ) : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Severity</th><th>Type</th><th>Source</th><th>Status</th><th>Summary</th><th>First seen</th><th>Last seen</th><th>Actions</th></tr></thead>
                <tbody>
                  {incidents.map((item) => (
                    <tr key={item.id} style={{ cursor: 'pointer' }} onClick={() => setSelectedId(item.id)}>
                      <td><StatusBadge tone={severityTone(item.severity)}>{item.severity.toUpperCase()}</StatusBadge></td>
                      <td>{item.incident_type}</td>
                      <td>{item.source_app}</td>
                      <td><StatusBadge tone={statusTone(item.status)}>{item.status}</StatusBadge></td>
                      <td>{item.summary || item.title}</td>
                      <td>{formatDate(item.first_seen_at)}</td>
                      <td>{formatDate(item.last_seen_at)}</td>
                      <td>{item.actions.length}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Incident detail" title={selected ? `Incident #${selected.id}` : 'Select an incident'} description="Metadata, mitigation history, recovery attempts, and related links.">
          {!selected ? (
            <EmptyState eyebrow="Detail" title="Select an incident" description="Pick one row to inspect mitigation and recovery traceability." />
          ) : (
            <div className="page-stack">
              <p><strong>Title:</strong> {selected.title}</p>
              <p><strong>Summary:</strong> {selected.summary || '—'}</p>
              <p><strong>Related object:</strong> {selected.related_object_type ?? '—'} / {selected.related_object_id ?? '—'}</p>
              <p><strong>Suggested links:</strong> <button type="button" className="link-button" onClick={() => navigate('/mission-control')}>Mission Control</button> · <button type="button" className="link-button" onClick={() => navigate('/runtime')}>Runtime</button> · <button type="button" className="link-button" onClick={() => navigate('/rollout')}>Rollout</button> · <button type="button" className="link-button" onClick={() => navigate('/alerts')}>Alerts</button></p>
              <div><strong>Metadata:</strong><pre>{JSON.stringify(selected.metadata ?? {}, null, 2)}</pre></div>
              <div>
                <strong>Mitigation history:</strong>
                {!selected.actions.length ? <p className="muted-text">No mitigation actions recorded yet.</p> : (
                  <ul>
                    {selected.actions.map((action) => (
                      <li key={action.id}><StatusBadge tone={statusTone(action.action_status)}>{action.action_status}</StatusBadge> <strong>{action.action_type}</strong> — {action.rationale}</li>
                    ))}
                  </ul>
                )}
              </div>
              <div>
                <strong>Recovery attempts:</strong>
                {!selected.recovery_runs.length ? <p className="muted-text">No recovery attempts yet.</p> : (
                  <ul>
                    {selected.recovery_runs.map((run) => (
                      <li key={run.id}><StatusBadge tone={statusTone(run.run_status)}>{run.run_status}</StatusBadge> — {run.summary}</li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          )}
        </SectionCard>
      </DataStateWrapper>
    </div>
  );
}

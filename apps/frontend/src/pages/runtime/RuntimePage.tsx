import { useCallback, useEffect, useState } from 'react';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { navigate } from '../../lib/router';
import { getIncidentSummary } from '../../services/incidents';
import {
  getRuntimeCapabilities,
  getRuntimeModes,
  getRuntimeStatus,
  getRuntimeTransitions,
  setRuntimeMode,
} from '../../services/runtime';
import type { RuntimeCapabilities, RuntimeModeOption, RuntimeStatusResponse, RuntimeTransition } from '../../types/runtime';
import type { IncidentSummary } from '../../types/incidents';

function tone(value: string) {
  if (value === 'PAPER_AUTO' || value === 'ACTIVE') return 'ready';
  if (value === 'PAPER_SEMI_AUTO' || value === 'DEGRADED' || value === 'PAPER_ASSIST' || value === 'PAUSED') return 'pending';
  if (value === 'OBSERVE_ONLY' || value === 'STOPPED') return 'offline';
  return 'neutral';
}

export function RuntimePage() {
  const [status, setStatus] = useState<RuntimeStatusResponse | null>(null);
  const [modes, setModes] = useState<RuntimeModeOption[]>([]);
  const [transitions, setTransitions] = useState<RuntimeTransition[]>([]);
  const [caps, setCaps] = useState<RuntimeCapabilities | null>(null);
  const [incidentSummary, setIncidentSummary] = useState<IncidentSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [statusRes, modesRes, transitionsRes, capsRes, incidentSummaryRes] = await Promise.all([
        getRuntimeStatus(),
        getRuntimeModes(),
        getRuntimeTransitions(),
        getRuntimeCapabilities(),
        getIncidentSummary(),
      ]);
      setStatus(statusRes);
      setModes(modesRes);
      setTransitions(transitionsRes);
      setCaps(capsRes);
      setIncidentSummary(incidentSummaryRes);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load runtime governance.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function onSetMode(mode: RuntimeModeOption['mode']) {
    setUpdating(mode);
    setError(null);
    try {
      await setRuntimeMode({ mode, set_by: 'operator', rationale: `Operator set mode to ${mode}.` });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not set runtime mode.');
    } finally {
      setUpdating(null);
    }
  }

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Runtime promotion controller"
        title="Runtime Governance"
        description="Explicit paper/demo runtime modes with auditable readiness and safety influence. No real-money enablement."
        actions={<div className="button-row"><button type="button" className="secondary-button" onClick={() => navigate('/readiness')}>Open Readiness</button><button type="button" className="secondary-button" onClick={() => navigate('/safety')}>Open Safety</button><button type="button" className="secondary-button" onClick={() => navigate('/alerts')}>Open Alerts</button><button type="button" className="secondary-button" onClick={() => navigate('/incidents')}>Open Incidents</button><button type="button" className="secondary-button" onClick={() => navigate('/mission-control')}>Open Mission Control</button><button type="button" className="secondary-button" onClick={() => navigate('/certification')}>Open Certification</button></div>}
      />

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Current mode" title="Runtime mode summary" description="Effective mode, status, and governance influence.">
          <div className="system-metadata-grid">
            <div><strong>Current mode:</strong> <StatusBadge tone={tone(status?.state.current_mode ?? 'UNKNOWN')}>{status?.state.current_mode ?? 'UNKNOWN'}</StatusBadge></div>
            <div><strong>Status:</strong> <StatusBadge tone={tone(status?.state.status ?? 'UNKNOWN')}>{status?.state.status ?? 'UNKNOWN'}</StatusBadge></div>
            <div><strong>Set by:</strong> {status?.state.set_by ?? '—'}</div>
            <div><strong>Rationale:</strong> {status?.state.rationale ?? '—'}</div>
            <div><strong>Readiness:</strong> {status?.readiness_status ?? 'No runs yet'}</div>
            <div><strong>Safety:</strong> {status?.safety_status.status ?? 'Unknown'} · {status?.safety_status.status_message ?? '—'}</div>
            <div><strong>Active incidents:</strong> {incidentSummary?.active_incidents ?? 0}</div>
            <div><strong>Critical incidents:</strong> {incidentSummary?.critical_active ?? 0}</div>
          </div>
        </SectionCard>

        <SectionCard eyebrow="Mode selector" title="Allowed runtime modes" description="Select conservative or autonomous paper modes. Blocked options show explicit reasons.">
          <div className="table-wrapper">
            <table className="data-table">
              <thead><tr><th>Mode</th><th>Description</th><th>Allowed now</th><th>Action</th></tr></thead>
              <tbody>
                {modes.map((mode) => (
                  <tr key={mode.mode}>
                    <td><StatusBadge tone={tone(mode.mode)}>{mode.mode}</StatusBadge></td>
                    <td>{mode.description}</td>
                    <td>{mode.is_allowed_now ? 'Yes' : `No · ${mode.blocked_reasons.join(' ') || 'Blocked'}`}</td>
                    <td>
                      <button type="button" className="secondary-button" disabled={!mode.is_allowed_now || updating === mode.mode} onClick={() => void onSetMode(mode.mode)}>
                        {updating === mode.mode ? 'Setting…' : 'Set mode'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionCard>

        <SectionCard eyebrow="Capabilities" title="Effective capabilities" description="What runtime can do under this mode after safety constraints.">
          <ul>
            <li>Auto execution allowed: {caps?.allow_auto_execution ? 'Yes' : 'No'}</li>
            <li>Operator required for all trades: {caps?.require_operator_for_all_trades ? 'Yes' : 'No'}</li>
            <li>Continuous loop allowed: {caps?.allow_continuous_loop ? 'Yes' : 'No'}</li>
            <li>Real-market ops (paper-only) allowed: {caps?.allow_real_market_ops ? 'Yes' : 'No'}</li>
            <li>Max auto trades per cycle/session: {caps?.max_auto_trades_per_cycle ?? 0} / {caps?.max_auto_trades_per_session ?? 0}</li>
          </ul>
          {caps?.blocked_reasons?.length ? <p>This mode is currently blocked by readiness or safety constraints: {caps.blocked_reasons.join(' ')}</p> : null}
        </SectionCard>

        <SectionCard eyebrow="Transitions" title="Recent runtime transitions" description="Audit trail for manual changes and automatic degradations.">
          {!transitions.length ? (
            <p>No transitions recorded yet.</p>
          ) : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>From</th><th>To</th><th>Source</th><th>Reason</th><th>Created</th></tr></thead>
                <tbody>
                  {transitions.slice(0, 20).map((transition) => (
                    <tr key={transition.id}>
                      <td>{transition.from_mode ?? '—'}</td>
                      <td>{transition.to_mode}</td>
                      <td>{transition.trigger_source}</td>
                      <td>{transition.reason}</td>
                      <td>{new Date(transition.created_at).toLocaleString()}</td>
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

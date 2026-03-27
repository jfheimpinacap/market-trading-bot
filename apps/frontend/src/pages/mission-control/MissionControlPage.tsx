import { useCallback, useEffect, useMemo, useState } from 'react';
import { EmptyState } from '../../components/EmptyState';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { navigate } from '../../lib/router';
import {
  getMissionControlCycles,
  getMissionControlStatus,
  pauseMissionControl,
  resumeMissionControl,
  runMissionControlCycle,
  startMissionControl,
  stopMissionControl,
} from '../../services/missionControl';
import type { MissionControlCycle, MissionControlStatusResponse } from '../../types/missionControl';

const formatDate = (v: string | null) => (v ? new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(v)) : 'Pending');
const tone = (v: string) => (v === 'RUNNING' || v === 'SUCCESS' ? 'ready' : v === 'PAUSED' || v === 'PARTIAL' ? 'pending' : v === 'FAILED' ? 'offline' : 'neutral');

export function MissionControlPage() {
  const [status, setStatus] = useState<MissionControlStatusResponse | null>(null);
  const [cycles, setCycles] = useState<MissionControlCycle[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [profile, setProfile] = useState('balanced_mission_control');

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [s, c] = await Promise.all([getMissionControlStatus(), getMissionControlCycles()]);
      setStatus(s);
      setCycles(c);
      if (s.state?.profile_slug) setProfile(s.state.profile_slug);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load mission control.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const runAction = useCallback(async (fn: () => Promise<unknown>, message: string) => {
    setActionLoading(true);
    setActionMessage(null);
    try {
      await fn();
      setActionMessage(message);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Mission control action failed.');
    } finally {
      setActionLoading(false);
    }
  }, [load]);

  const runtimeStatus = status?.state?.status ?? 'IDLE';
  const controls = useMemo(() => ({
    canStart: runtimeStatus !== 'RUNNING',
    canPause: runtimeStatus === 'RUNNING',
    canResume: runtimeStatus === 'PAUSED',
    canStop: runtimeStatus === 'RUNNING' || runtimeStatus === 'PAUSED' || runtimeStatus === 'DEGRADED',
  }), [runtimeStatus]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Mission control"
        title="/mission-control"
        description="Autonomous operations scheduler / closed-loop supervision for paper/demo-only operation. Explicit and auditable, no real-money execution."
        actions={<div className="button-row"><button type="button" className="secondary-button" onClick={() => navigate('/runtime')}>Open Runtime</button><button type="button" className="secondary-button" onClick={() => navigate('/opportunities')}>Open Opportunities</button><button type="button" className="secondary-button" onClick={() => navigate('/alerts')}>Open Alerts</button><button type="button" className="secondary-button" onClick={() => navigate('/incidents')}>Open Incidents</button><button type="button" className="secondary-button" onClick={() => navigate('/notifications')}>Open Notifications</button><button type="button" className="secondary-button" onClick={() => navigate('/portfolio-governor')}>Open Portfolio Governor</button><button type="button" className="secondary-button" onClick={() => navigate('/profile-manager')}>Open Profile Manager</button><button type="button" className="secondary-button" onClick={() => navigate('/promotion')}>Open Promotion</button><button type="button" className="secondary-button" onClick={() => navigate('/rollout')}>Open Rollout</button></div>}
      />

      <SectionCard eyebrow="Control panel" title="Session controls" description="Start, pause, resume, stop, and run one cycle with explicit profile selection.">
        <div className="button-row">
          <label className="field-group"><span>Profile</span><select className="select-input" value={profile} onChange={(e) => setProfile(e.target.value)}>{(status?.profiles ?? []).map((p) => <option key={p.slug} value={p.slug}>{p.label}</option>)}</select></label>
          <button type="button" className="primary-button" disabled={actionLoading || !controls.canStart} onClick={() => runAction(() => startMissionControl({ profile_slug: profile }), 'Mission control started.')}>Start</button>
          <button type="button" className="secondary-button" disabled={actionLoading || !controls.canPause} onClick={() => runAction(() => pauseMissionControl(), 'Mission control paused.')}>Pause</button>
          <button type="button" className="secondary-button" disabled={actionLoading || !controls.canResume} onClick={() => runAction(() => resumeMissionControl(), 'Mission control resumed.')}>Resume</button>
          <button type="button" className="ghost-button" disabled={actionLoading || !controls.canStop} onClick={() => runAction(() => stopMissionControl(), 'Mission control stop requested.')}>Stop</button>
          <button type="button" className="ghost-button" disabled={actionLoading} onClick={() => runAction(() => runMissionControlCycle({ profile_slug: profile }), 'Cycle completed.')}>Run one cycle</button>
        </div>
        {actionMessage ? <p>{actionMessage}</p> : null}
        {status?.safety?.kill_switch_enabled || status?.safety?.hard_stop_active ? <p><strong>Safety influence:</strong> {status?.safety?.status} · {status?.safety?.status_message ?? 'Guardrail active.'}</p> : null}
      </SectionCard>

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <div className="content-grid content-grid--two-columns">
          <SectionCard eyebrow="Current state" title="Mission runtime" description="What is running now and why.">
            <div className="system-metadata-grid">
              <div><strong>Status:</strong> <StatusBadge tone={tone(runtimeStatus)}>{runtimeStatus}</StatusBadge></div>
              <div><strong>Active session:</strong> {status?.active_session?.id ?? 'None'}</div>
              <div><strong>Last cycle:</strong> {formatDate(status?.latest_cycle?.finished_at ?? null)}</div>
              <div><strong>Cycle interval:</strong> {String(status?.state?.settings_snapshot?.cycle_interval_seconds ?? 'n/a')} sec</div>
              <div><strong>Runtime mode:</strong> {status?.runtime?.current_mode ?? 'UNKNOWN'}</div>
              <div><strong>Safety status:</strong> {status?.safety?.status ?? 'UNKNOWN'}</div>
              <div><strong>Kill switch:</strong> {status?.safety?.kill_switch_enabled ? 'ON' : 'OFF'}</div>
              <div><strong>Cycle in progress:</strong> {status?.state?.cycle_in_progress ? 'yes' : 'no'}</div>
              <div><strong>Rollout status:</strong> {status?.rollout?.current_status ?? 'None'}</div>
              <div><strong>Rollout canary %:</strong> {status?.rollout?.canary_percentage ?? 0}%</div>
              <div><strong>Active incidents:</strong> {status?.incident_summary?.active_incidents ?? 0}</div>
              <div><strong>Degraded mode:</strong> {status?.degraded_mode?.state ?? 'normal'}</div>
            </div>
          </SectionCard>

          <SectionCard eyebrow="Latest step trace" title="Cycle step visibility" description="Audit-friendly breakdown of the latest cycle.">
            {!status?.latest_cycle?.steps?.length ? <p className="muted-text">Start mission control to begin autonomous paper operations.</p> : (
              <ul>
                {status.latest_cycle.steps.map((step) => <li key={step.id}><StatusBadge tone={tone(step.status)}>{step.status}</StatusBadge> <strong>{step.step_type}</strong> — {step.summary}</li>)}
              </ul>
            )}
          </SectionCard>
        </div>

        <SectionCard eyebrow="Recent cycles" title="Cycle history" description="Status, timing, and queue/auto/blocked outcomes for mission loops.">
          {cycles.length === 0 ? (
            <EmptyState title="No mission control cycles yet" description="Start mission control to begin autonomous paper operations." eyebrow="Mission control" />
          ) : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Cycle</th><th>Status</th><th>Started</th><th>Finished</th><th>Opportunities</th><th>Queue</th><th>Auto</th><th>Blocked</th><th>Summary</th></tr></thead>
                <tbody>
                  {cycles.slice(0, 15).map((cycle) => (
                    <tr key={cycle.id}>
                      <td>{cycle.cycle_number}</td>
                      <td><StatusBadge tone={tone(cycle.status)}>{cycle.status}</StatusBadge></td>
                      <td>{formatDate(cycle.started_at)}</td>
                      <td>{formatDate(cycle.finished_at)}</td>
                      <td>{cycle.opportunities_built}</td>
                      <td>{cycle.queue_count}</td>
                      <td>{cycle.auto_execute_count}</td>
                      <td>{cycle.blocked_count}</td>
                      <td>{cycle.summary}</td>
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

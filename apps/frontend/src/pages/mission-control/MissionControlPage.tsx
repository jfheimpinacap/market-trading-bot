import { useCallback, useEffect, useMemo, useState } from 'react';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import {
  getAutonomousCadenceDecisions,
  getAutonomousSessionRecommendations,
  getAutonomousSessionSummary,
  getAutonomousSessions,
  getAutonomousTicks,
  pauseAutonomousSession,
  resumeAutonomousSession,
  runAutonomousTick,
  startAutonomousSession,
  stopAutonomousSession,
} from '../../services/missionControl';
import type {
  AutonomousCadenceDecision,
  AutonomousRuntimeSession,
  AutonomousRuntimeTick,
  AutonomousSessionRecommendation,
  AutonomousSessionSummary,
} from '../../types/missionControl';

export function MissionControlPage() {
  const [sessions, setSessions] = useState<AutonomousRuntimeSession[]>([]);
  const [ticks, setTicks] = useState<AutonomousRuntimeTick[]>([]);
  const [decisions, setDecisions] = useState<AutonomousCadenceDecision[]>([]);
  const [recommendations, setRecommendations] = useState<AutonomousSessionRecommendation[]>([]);
  const [summary, setSummary] = useState<AutonomousSessionSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const activeSession = useMemo(() => sessions.find((session) => session.session_status === 'RUNNING') ?? sessions[0] ?? null, [sessions]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [loadedSessions, loadedTicks, loadedDecisions, loadedRecommendations, loadedSummary] = await Promise.all([
        getAutonomousSessions(),
        getAutonomousTicks(),
        getAutonomousCadenceDecisions(),
        getAutonomousSessionRecommendations(),
        getAutonomousSessionSummary(),
      ]);
      setSessions(loadedSessions);
      setTicks(loadedTicks);
      setDecisions(loadedDecisions);
      setRecommendations(loadedRecommendations);
      setSummary(loadedSummary);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load autonomous session runtime state.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Mission control"
        title="Autonomous Session Control"
        description="Persistent paper-only autonomous session layer with cadence-aware tick governance, pause/resume/stop controls, and transparent cooldown-aware traceability. No live execution."
        actions={<div className="button-row"><button type="button" className="primary-button" onClick={async () => { await startAutonomousSession({}); await load(); }}>Start session</button><button type="button" className="secondary-button" disabled={!activeSession} onClick={async () => { if (activeSession) { await runAutonomousTick(activeSession.id); await load(); } }}>Run tick</button><button type="button" className="secondary-button" disabled={!activeSession} onClick={async () => { if (activeSession) { await pauseAutonomousSession(activeSession.id); await load(); } }}>Pause</button><button type="button" className="secondary-button" disabled={!activeSession} onClick={async () => { if (activeSession) { await resumeAutonomousSession(activeSession.id); await load(); } }}>Resume</button><button type="button" className="secondary-button" disabled={!activeSession} onClick={async () => { if (activeSession) { await stopAutonomousSession(activeSession.id); await load(); } }}>Stop</button></div>}
      />

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Summary" title="Session governance counters" description="Continuous governed paper runtime summary for persistent autonomous sessions.">
          <div className="system-metadata-grid">
            <div><strong>Active sessions:</strong> {summary?.active_sessions ?? 0}</div>
            <div><strong>Paused sessions:</strong> {summary?.paused_sessions ?? 0}</div>
            <div><strong>Stopped sessions:</strong> {summary?.stopped_sessions ?? 0}</div>
            <div><strong>Total sessions:</strong> {summary?.session_count ?? 0}</div>
            <div><strong>Ticks executed:</strong> {summary?.ticks_executed ?? 0}</div>
            <div><strong>Ticks skipped:</strong> {summary?.ticks_skipped ?? 0}</div>
            <div><strong>Dispatches:</strong> {summary?.dispatch_count ?? 0}</div>
            <div><strong>Closed outcomes:</strong> {summary?.closed_outcome_count ?? 0}</div>
          </div>
        </SectionCard>

        <SectionCard eyebrow="Sessions" title="Autonomous runtime sessions" description="Lifecycle and posture of each persistent autonomous session.">
          <ul>{sessions.slice(0, 8).map((session) => <li key={session.id}><StatusBadge tone="ready">{session.session_status}</StatusBadge> session={session.id} mode={session.runtime_mode || 'unknown'} profile={session.profile_slug || 'default'} ticks={session.tick_count} dispatch={session.dispatch_count} updated={session.updated_at}</li>)}</ul>
        </SectionCard>

        <SectionCard eyebrow="Ticks" title="Autonomous runtime ticks" description="Cadence-aware tick executions linked to runtime and cycle outcomes.">
          <ul>{ticks.slice(0, 10).map((tick) => <li key={tick.id}><StatusBadge tone="pending">{tick.tick_status}</StatusBadge> session={tick.linked_session} tick#{tick.tick_index} mode={tick.planned_tick_mode} runtime={tick.linked_runtime_run ?? 'n/a'} outcome={tick.linked_cycle_outcome ?? 'n/a'} summary={tick.tick_summary || 'n/a'}</li>)}</ul>
        </SectionCard>

        <SectionCard eyebrow="Cadence" title="Cadence decisions" description="Transparent cadence decisions based on portfolio/runtime/safety posture and signal pressure.">
          <ul>{decisions.slice(0, 10).map((decision) => <li key={decision.id}><strong>{decision.cadence_mode}</strong> — portfolio={decision.portfolio_posture || 'n/a'} runtime={decision.runtime_posture || 'n/a'} safety={decision.safety_posture || 'n/a'} signal={decision.signal_pressure_state} summary={decision.decision_summary}</li>)}</ul>
        </SectionCard>

        <SectionCard eyebrow="Recommendations" title="Session recommendations" description="Conservative next actions for pause/stop/reduced cadence under pressure or hard blocks.">
          <ul>{recommendations.slice(0, 10).map((recommendation) => <li key={recommendation.id}><strong>{recommendation.recommendation_type}</strong> — {recommendation.rationale} blockers=[{recommendation.blockers.join(', ')}] confidence={recommendation.confidence}</li>)}</ul>
        </SectionCard>
      </DataStateWrapper>
    </div>
  );
}

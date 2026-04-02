import { useCallback, useEffect, useMemo, useState } from 'react';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import {
  getAutonomousHeartbeatDecisions,
  getAutonomousHeartbeatRecommendations,
  getAutonomousHeartbeatRuns,
  getAutonomousHeartbeatSummary,
  getAutonomousRunnerState,
  getAutonomousSessionSummary,
  getAutonomousSessions,
  getAutonomousTickDispatchAttempts,
  pauseAutonomousRunner,
  resumeAutonomousRunner,
  runAutonomousHeartbeat,
  startAutonomousRunner,
  stopAutonomousRunner,
} from '../../services/missionControl';
import type {
  AutonomousHeartbeatDecision,
  AutonomousHeartbeatRecommendation,
  AutonomousHeartbeatRun,
  AutonomousHeartbeatSummary,
  AutonomousRunnerState,
  AutonomousRuntimeSession,
  AutonomousSessionSummary,
  AutonomousTickDispatchAttempt,
} from '../../types/missionControl';

export function MissionControlPage() {
  const [sessions, setSessions] = useState<AutonomousRuntimeSession[]>([]);
  const [runnerState, setRunnerState] = useState<AutonomousRunnerState | null>(null);
  const [heartbeatRuns, setHeartbeatRuns] = useState<AutonomousHeartbeatRun[]>([]);
  const [decisions, setDecisions] = useState<AutonomousHeartbeatDecision[]>([]);
  const [dispatchAttempts, setDispatchAttempts] = useState<AutonomousTickDispatchAttempt[]>([]);
  const [recommendations, setRecommendations] = useState<AutonomousHeartbeatRecommendation[]>([]);
  const [summary, setSummary] = useState<AutonomousSessionSummary | null>(null);
  const [heartbeatSummary, setHeartbeatSummary] = useState<AutonomousHeartbeatSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const latestHeartbeat = useMemo(() => heartbeatRuns[0] ?? null, [heartbeatRuns]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [loadedSessions, loadedSummary, loadedRunnerState, loadedRuns, loadedDecisions, loadedDispatches, loadedRecommendations, loadedHeartbeatSummary] = await Promise.all([
        getAutonomousSessions(),
        getAutonomousSessionSummary(),
        getAutonomousRunnerState(),
        getAutonomousHeartbeatRuns(),
        getAutonomousHeartbeatDecisions(),
        getAutonomousTickDispatchAttempts(),
        getAutonomousHeartbeatRecommendations(),
        getAutonomousHeartbeatSummary(),
      ]);
      setSessions(loadedSessions);
      setSummary(loadedSummary);
      setRunnerState(loadedRunnerState);
      setHeartbeatRuns(loadedRuns);
      setDecisions(loadedDecisions);
      setDispatchAttempts(loadedDispatches);
      setRecommendations(loadedRecommendations);
      setHeartbeatSummary(loadedHeartbeatSummary);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load autonomous heartbeat runner state.');
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
        title="Autonomous Runner"
        description="Local-first heartbeat runner that advances RUNNING autonomous sessions automatically when cadence is due, with cooldown/safety/runtime guardrails and paper-only execution boundaries."
        actions={<div className="button-row"><button type="button" className="primary-button" onClick={async () => { await startAutonomousRunner(); await load(); }}>Start runner</button><button type="button" className="secondary-button" onClick={async () => { await pauseAutonomousRunner(); await load(); }}>Pause runner</button><button type="button" className="secondary-button" onClick={async () => { await resumeAutonomousRunner(); await load(); }}>Resume runner</button><button type="button" className="secondary-button" onClick={async () => { await stopAutonomousRunner(); await load(); }}>Stop runner</button><button type="button" className="secondary-button" onClick={async () => { await runAutonomousHeartbeat(); await load(); }}>Run heartbeat now</button></div>}
      />

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Autonomous runner" title="Heartbeat summary" description="Paper-only local heartbeat progression. No live broker/exchange execution.">
          <div className="system-metadata-grid">
            <div><strong>Runner status:</strong> {runnerState?.runner_status ?? 'n/a'}</div>
            <div><strong>Active sessions:</strong> {runnerState?.active_session_count ?? 0}</div>
            <div><strong>Considered sessions:</strong> {latestHeartbeat?.considered_session_count ?? 0}</div>
            <div><strong>Due ticks:</strong> {latestHeartbeat?.due_tick_count ?? 0}</div>
            <div><strong>Executed ticks:</strong> {latestHeartbeat?.executed_tick_count ?? 0}</div>
            <div><strong>Cooldown skips:</strong> {latestHeartbeat?.cooldown_skip_count ?? 0}</div>
            <div><strong>Blocked / paused / stopped:</strong> {(latestHeartbeat?.blocked_count ?? 0) + (latestHeartbeat?.paused_count ?? 0) + (latestHeartbeat?.stopped_count ?? 0)}</div>
            <div><strong>Total heartbeat runs:</strong> {heartbeatSummary?.totals.heartbeat_runs ?? 0}</div>
          </div>
        </SectionCard>

        <SectionCard eyebrow="Runner state" title="Local autonomous runner state" description="Single local runner state with audit timestamps.">
          <ul>
            <li><StatusBadge tone="ready">{runnerState?.runner_status ?? 'UNKNOWN'}</StatusBadge> runner={runnerState?.runner_name ?? 'n/a'} last_heartbeat={runnerState?.last_heartbeat_at ?? 'n/a'} last_success={runnerState?.last_successful_run_at ?? 'n/a'} active_sessions={runnerState?.active_session_count ?? 0}</li>
          </ul>
        </SectionCard>

        <SectionCard eyebrow="Heartbeat decisions" title="Due tick decisions by session" description="Transparent due/wait/cooldown/pause/stop/block decisions for every evaluated session.">
          <ul>{decisions.slice(0, 12).map((decision) => <li key={decision.id}><strong>{decision.decision_type}</strong> — session={decision.linked_session} due_now={String(decision.due_now)} next_due={decision.next_due_at ?? 'n/a'} status={decision.decision_status} summary={decision.decision_summary}</li>)}</ul>
        </SectionCard>

        <SectionCard eyebrow="Tick dispatch attempts" title="Automatic dispatch traceability" description="Automatic/manual distinction and status for each heartbeat dispatch attempt.">
          <ul>{dispatchAttempts.slice(0, 12).map((attempt) => <li key={attempt.id}><strong>{attempt.dispatch_status}</strong> — session={attempt.linked_session} tick={attempt.linked_tick ?? 'n/a'} automatic={String(attempt.automatic)} summary={attempt.summary}</li>)}</ul>
        </SectionCard>

        <SectionCard eyebrow="Recommendations" title="Heartbeat recommendations" description="Conservative recommendations emitted per heartbeat decision.">
          <ul>{recommendations.slice(0, 12).map((recommendation) => <li key={recommendation.id}><strong>{recommendation.recommendation_type}</strong> — {recommendation.rationale} blockers=[{recommendation.blockers.join(', ')}] confidence={recommendation.confidence}</li>)}</ul>
        </SectionCard>

        <SectionCard eyebrow="Session baseline" title="Autonomous session counters" description="Existing autonomous session counters remain available for manual/automatic coexistence.">
          <div className="system-metadata-grid">
            <div><strong>Total sessions:</strong> {summary?.session_count ?? 0}</div>
            <div><strong>Active sessions:</strong> {summary?.active_sessions ?? 0}</div>
            <div><strong>Paused sessions:</strong> {summary?.paused_sessions ?? 0}</div>
            <div><strong>Stopped sessions:</strong> {summary?.stopped_sessions ?? 0}</div>
            <div><strong>Ticks executed:</strong> {summary?.ticks_executed ?? 0}</div>
            <div><strong>Ticks skipped:</strong> {summary?.ticks_skipped ?? 0}</div>
            <div><strong>Dispatches:</strong> {summary?.dispatch_count ?? 0}</div>
            <div><strong>Closed outcomes:</strong> {summary?.closed_outcome_count ?? 0}</div>
          </div>
          <ul>{sessions.slice(0, 8).map((session) => <li key={session.id}><StatusBadge tone="pending">{session.session_status}</StatusBadge> session={session.id} mode={session.runtime_mode || 'unknown'} profile={session.profile_slug || 'default'} ticks={session.tick_count}</li>)}</ul>
        </SectionCard>
      </DataStateWrapper>
    </div>
  );
}

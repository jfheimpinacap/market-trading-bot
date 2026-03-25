import { useCallback, useEffect, useMemo, useState } from 'react';
import { EmptyState } from '../../components/EmptyState';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { publishDemoFlowRefresh } from '../../lib/demoFlow';
import { navigate } from '../../lib/router';
import { getOperatorQueueSummary } from '../../services/operatorQueue';
import { getSafetyStatus } from '../../services/safety';
import type { SafetyStatus } from '../../types/safety';
import {
  getContinuousDemoCycles,
  getContinuousDemoStatus,
  pauseContinuousDemo,
  resumeContinuousDemo,
  runSingleDemoCycle,
  startContinuousDemo,
  stopContinuousDemo,
} from '../../services/continuousDemo';
import type { ContinuousDemoCycleRun, ContinuousDemoStatus } from '../../types/continuousDemo';

function getErrorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

function formatDate(value: string | null) {
  if (!value) return 'Pending';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short' }).format(date);
}

function statusTone(value: string) {
  if (value === 'RUNNING' || value === 'SUCCESS') return 'ready';
  if (value === 'PAUSED' || value === 'PARTIAL') return 'pending';
  if (value === 'FAILED') return 'offline';
  return 'neutral';
}

export function ContinuousDemoPage() {
  const [status, setStatus] = useState<ContinuousDemoStatus | null>(null);
  const [cycles, setCycles] = useState<ContinuousDemoCycleRun[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isActionLoading, setIsActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [safety, setSafety] = useState<SafetyStatus | null>(null);
  const [queuePending, setQueuePending] = useState(0);

  const loadState = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [statusResponse, cyclesResponse, safetyResponse, queueSummary] = await Promise.all([getContinuousDemoStatus(), getContinuousDemoCycles(), getSafetyStatus(), getOperatorQueueSummary()]);
      setStatus(statusResponse);
      setCycles(cyclesResponse);
      setSafety(safetyResponse);
      setQueuePending(queueSummary.pending_count);
    } catch (loadError) {
      setError(getErrorMessage(loadError, 'Could not load continuous demo status.'));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadState();
  }, [loadState]);

  const doAction = useCallback(async (fn: () => Promise<unknown>, message: string) => {
    setIsActionLoading(true);
    setActionMessage(null);
    setError(null);
    try {
      await fn();
      setActionMessage(message);
      publishDemoFlowRefresh('continuous-demo');
      await loadState();
    } catch (actionError) {
      setError(getErrorMessage(actionError, 'Continuous demo action failed.'));
    } finally {
      setIsActionLoading(false);
    }
  }, [loadState]);

  const runtimeStatus = status?.runtime?.runtime_status ?? 'IDLE';
  const activeSession = status?.active_session;
  const latestCycle = status?.latest_cycle;

  const controls = useMemo(() => ({
    canStart: runtimeStatus !== 'RUNNING' && !safety?.kill_switch_enabled && !safety?.hard_stop_active,
    canPause: runtimeStatus === 'RUNNING',
    canResume: runtimeStatus === 'PAUSED' && !safety?.kill_switch_enabled,
    canStop: runtimeStatus === 'RUNNING' || runtimeStatus === 'PAUSED',
  }), [runtimeStatus, safety]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Autonomous continuous demo"
        title="Continuous Demo"
        description="Loop autónomo continuo para market → signal → proposal → policy/risk → semi-auto paper execution → review. Paper/demo only; nunca trading real."
        actions={<div className="button-row"><button type="button" className="secondary-button" onClick={() => navigate('/allocation')}>Open Allocation</button><button type="button" className="secondary-button" onClick={() => navigate('/semi-auto')}>Open Semi-Auto</button><button type="button" className="secondary-button" onClick={() => navigate('/real-ops')}>Open Real Ops</button></div>}
      />

      <SectionCard eyebrow="Runtime control" title="Loop controls" description="Gestiona start, pause, resume, stop y ejecución manual de un ciclo.">
        {safety?.kill_switch_enabled || safety?.hard_stop_active || safety?.cooldown_until_cycle ? <p><strong>Safety restriction:</strong> Auto execution constrained ({safety?.status}). {safety?.status_message}</p> : null}
        <div className="button-row">
          <button type="button" className="primary-button" disabled={isActionLoading || !controls.canStart} onClick={() => doAction(() => startContinuousDemo({ cycle_interval_seconds: 30 }), 'Continuous demo loop started.')}>Start loop</button>
          <button type="button" className="secondary-button" disabled={isActionLoading || !controls.canPause} onClick={() => doAction(() => pauseContinuousDemo(), 'Loop paused.')}>Pause loop</button>
          <button type="button" className="secondary-button" disabled={isActionLoading || !controls.canResume} onClick={() => doAction(() => resumeContinuousDemo(), 'Loop resumed.')}>Resume loop</button>
          <button type="button" className="ghost-button" disabled={isActionLoading || !controls.canStop} onClick={() => doAction(() => stopContinuousDemo(false), 'Stop requested.')}>Stop loop</button>
          <button type="button" className="ghost-button" disabled={isActionLoading} onClick={() => doAction(() => runSingleDemoCycle(), 'Single cycle finished.')}>Run single cycle</button>
          <button type="button" className="ghost-button" disabled={isActionLoading} onClick={() => doAction(() => stopContinuousDemo(true), 'Kill switch activated.')}>Kill switch</button>
        </div>
        {actionMessage ? <p>{actionMessage}</p> : null}
      </SectionCard>

      <DataStateWrapper isLoading={isLoading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <div className="content-grid content-grid--two-columns">
          <SectionCard eyebrow="Current status" title="Runtime snapshot" description="Estado actual del loop continuo y la sesión activa.">
            <div className="system-metadata-grid">
              <div><strong>Status:</strong> <StatusBadge tone={statusTone(runtimeStatus)}>{runtimeStatus}</StatusBadge></div>
              <div><strong>Session ID:</strong> {activeSession?.id ?? 'None'}</div>
              <div><strong>Cycle interval:</strong> {String(activeSession?.settings_snapshot?.cycle_interval_seconds ?? 30)} sec</div>
              <div><strong>Last cycle:</strong> {formatDate(activeSession?.last_cycle_at ?? null)}</div>
              <div><strong>Total cycles:</strong> {activeSession?.total_cycles ?? 0}</div>
              <div><strong>Auto executed:</strong> {activeSession?.total_auto_executed ?? 0}</div>
              <div><strong>Pending approvals:</strong> {activeSession?.total_pending_approvals ?? status?.pending_approvals ?? 0}</div>
              <div><strong>Blocked:</strong> {activeSession?.total_blocked ?? 0}</div>
              <div><strong>Errors:</strong> {activeSession?.total_errors ?? 0}</div>
              <div><strong>Learning rebuild:</strong> {activeSession?.settings_snapshot?.learning_rebuild_enabled ? 'automatic (conservative)' : 'manual only'}</div>
              <div><strong>Learning cadence:</strong> every {String(activeSession?.settings_snapshot?.learning_rebuild_every_n_cycles ?? '—')} cycles</div>
            </div>
          </SectionCard>

          <SectionCard eyebrow="Safety" title="Active guardrails" description="Recordatorio explícito de límites y seguridad del loop.">
            <ul>
              <li>Execution mode: paper/demo only</li>
              <li>Real exchange execution: disabled</li>
              <li>Market scope: {String(activeSession?.settings_snapshot?.market_scope ?? 'mixed')}</li>
              <li>Max auto trades per cycle: {String(activeSession?.settings_snapshot?.max_auto_trades_per_cycle ?? 2)}</li>
              <li>Max auto trades per session: {String(activeSession?.settings_snapshot?.max_auto_trades_total_per_session ?? 20)}</li>
              <li>APPROVAL_REQUIRED → PendingApproval queue</li>
              <li>Safety status: {safety?.status ?? 'UNKNOWN'}</li>
              <li>Cooldown active: {safety?.cooldown_until_cycle ? `until cycle ${safety.cooldown_until_cycle}` : 'no'}</li>
              <li>HARD_BLOCK → never executed</li>
              <li>Automatic learning rebuild: {activeSession?.settings_snapshot?.learning_rebuild_enabled ? 'enabled' : 'disabled for safety'}</li>
            </ul>
          </SectionCard>
        </div>

        <SectionCard eyebrow="Learning integration" title="Controlled learning loop status" description="Continuous demo can trigger rebuild conservatively, never by aggressive per-cycle auto-optimization.">
          <ul>
            <li>Mode: {activeSession?.settings_snapshot?.learning_rebuild_enabled ? 'Enabled' : 'Disabled (manual recommended default)'}</li>
            <li>Every N cycles: {String(activeSession?.settings_snapshot?.learning_rebuild_every_n_cycles ?? 'not configured')}</li>
            <li>After reviews: {activeSession?.settings_snapshot?.learning_rebuild_after_reviews ? 'enabled' : 'disabled'}</li>
            <li>Latest cycle learning hook: {String((latestCycle?.details as Record<string, unknown> | undefined)?.learning_rebuild ? 'recorded' : 'not triggered')}</li>
            <li>Automatic rebuild is disabled for safety unless explicitly enabled with conservative cadence.</li>
          </ul>
        </SectionCard>

        <SectionCard eyebrow="Pending approvals" title="Manual queue snapshot" description="El loop respeta la cola manual de aprobaciones y no ejecuta propuestas no elegibles automáticamente.">
          <p><strong>PENDING approvals:</strong> {status?.pending_approvals ?? 0}</p>
          <p><strong>Operator queue pending exceptions:</strong> {queuePending}</p>
          <button type="button" className="secondary-button" onClick={() => navigate('/operator-queue')}>Open /operator-queue</button>
        </SectionCard>

        <SectionCard eyebrow="Recent cycles" title="Cycle history" description={latestCycle?.summary ?? 'Cada ciclo queda trazado para auditoría y debugging.'}>
          {cycles.length === 0 ? (
            <EmptyState title="No cycle runs yet" description="Use Run single cycle or start the loop to create auditable runs." eyebrow="Cycles" />
          ) : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Cycle #</th>
                    <th>Status</th>
                    <th>Started</th>
                    <th>Finished</th>
                    <th>Proposals</th>
                    <th>Auto</th>
                    <th>Pending</th>
                    <th>Blocked</th>
                  </tr>
                </thead>
                <tbody>
                  {cycles.slice(0, 12).map((cycle) => (
                    <tr key={cycle.id}>
                      <td>{cycle.cycle_number}</td>
                      <td><StatusBadge tone={statusTone(cycle.status)}>{cycle.status}</StatusBadge></td>
                      <td>{formatDate(cycle.started_at)}</td>
                      <td>{formatDate(cycle.finished_at)}</td>
                      <td>{cycle.proposals_generated}</td>
                      <td>{cycle.auto_executed_count}</td>
                      <td>{cycle.approval_required_count}</td>
                      <td>{cycle.blocked_count}</td>
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

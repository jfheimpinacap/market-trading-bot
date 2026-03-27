import { useCallback, useEffect, useMemo, useState } from 'react';

import { EmptyState } from '../../components/EmptyState';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { navigate } from '../../lib/router';
import { createStackRolloutPlan, getCurrentRollout, getRolloutRuns, getRolloutSummary, pauseRollout, resumeRollout, rollbackRollout, startRollout } from '../../services/rollout';
import type { RolloutDecisionCode, StackRolloutRun, StackRolloutRunStatus } from '../../types/rollout';

const statusClass = (status: string) => {
  if (status === 'RUNNING' || status === 'CONTINUE_ROLLOUT') return 'signal-badge signal-badge--actionable';
  if (status === 'PAUSED' || status === 'EXTEND_CANARY') return 'signal-badge signal-badge--monitor';
  if (status === 'ROLLED_BACK' || status === 'ROLLBACK_NOW') return 'signal-badge signal-badge--bearish';
  return 'signal-badge signal-badge--neutral';
};

export function RolloutPage() {
  const [current, setCurrent] = useState<StackRolloutRun | null>(null);
  const [runs, setRuns] = useState<StackRolloutRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const [candidateBindingId, setCandidateBindingId] = useState(0);
  const [mode, setMode] = useState<'SHADOW_ONLY' | 'CANARY' | 'STAGED'>('CANARY');
  const [canaryPercentage, setCanaryPercentage] = useState(20);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [currentRes, runsRes] = await Promise.all([getCurrentRollout(), getRolloutRuns()]);
      setCurrent(currentRes.current_rollout);
      setRuns(runsRes);
      await getRolloutSummary();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load rollout manager state.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const latestDecision = useMemo(() => current?.decisions?.[0]?.decision ?? null, [current]);

  const runAction = useCallback(async (fn: () => Promise<unknown>, okMessage: string) => {
    setActionLoading(true);
    setMessage(null);
    try {
      await fn();
      setMessage(okMessage);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Rollout action failed.');
    } finally {
      setActionLoading(false);
    }
  }, [load]);

  const onCreatePlan = useCallback(async () => {
    await runAction(async () => {
      const plan = await createStackRolloutPlan({
        candidate_binding_id: candidateBindingId,
        mode,
        canary_percentage: canaryPercentage,
        metadata: { initiated_from: 'rollout_ui', paper_demo_only: true },
      });
      await startRollout(plan.id, { initiated_from: 'rollout_ui_start' });
    }, 'Rollout plan created and started.');
  }, [candidateBindingId, canaryPercentage, mode, runAction]);

  const currentStatus = current?.status as StackRolloutRunStatus | undefined;
  const currentId = current?.id;

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Stack rollout manager"
        title="/rollout"
        description="Formal canary promotion and rollback guardrails for paper/demo stack evolution. This page is paper/demo only and never executes real money."
        actions={<div className="button-row"><button className="secondary-button" type="button" onClick={() => navigate('/promotion')}>Open Promotion</button><button className="secondary-button" type="button" onClick={() => navigate('/champion-challenger')}>Open Champion Challenger</button><button className="secondary-button" type="button" onClick={() => navigate('/mission-control')}>Open Mission Control</button><button className="secondary-button" type="button" onClick={() => navigate('/runtime')}>Open Runtime</button><button className="secondary-button" type="button" onClick={() => navigate('/incidents')}>Open Incidents</button></div>}
      />

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Current rollout" title="Active canary state" description="Current plan/run status, phase and distribution over paper opportunity flow.">
          {!current ? <p className="muted-text">Create a rollout plan to promote a challenger gradually.</p> : (
            <div className="system-metadata-grid">
              <div><strong>Status:</strong> <span className={statusClass(current.status)}>{current.status}</span></div>
              <div><strong>Mode:</strong> <span className={statusClass(current.plan.mode)}>{current.plan.mode}</span></div>
              <div><strong>Canary percentage:</strong> {current.plan.canary_percentage}%</div>
              <div><strong>Current phase:</strong> {current.current_phase}</div>
              <div><strong>Champion binding:</strong> {current.plan.champion_binding.name}</div>
              <div><strong>Candidate binding:</strong> {current.plan.candidate_binding.name}</div>
              <div><strong>Routed opportunities:</strong> {current.routed_opportunities_count}</div>
              <div><strong>Canary count:</strong> {current.canary_count}</div>
            </div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Controls" title="Plan + rollout actions" description="Explicit controls for create/start/pause/resume/rollback. No opaque auto-switching.">
          <div className="button-row">
            <label className="field-group"><span>Candidate binding id</span><input className="text-input" type="number" min={1} value={candidateBindingId || ''} onChange={(e) => setCandidateBindingId(Number(e.target.value) || 0)} /></label>
            <label className="field-group"><span>Mode</span><select className="select-input" value={mode} onChange={(e) => setMode(e.target.value as 'SHADOW_ONLY' | 'CANARY' | 'STAGED')}><option value="CANARY">CANARY</option><option value="SHADOW_ONLY">SHADOW_ONLY</option><option value="STAGED">STAGED</option></select></label>
            <label className="field-group"><span>Canary %</span><input className="text-input" type="number" min={0} max={100} value={canaryPercentage} onChange={(e) => setCanaryPercentage(Number(e.target.value) || 0)} /></label>
            <button className="primary-button" type="button" disabled={actionLoading || !candidateBindingId} onClick={() => void onCreatePlan()}>{actionLoading ? 'Working…' : 'Create plan + start'}</button>
            <button className="secondary-button" type="button" disabled={actionLoading || !currentId || currentStatus !== 'RUNNING'} onClick={() => currentId && runAction(() => pauseRollout(currentId), 'Rollout paused.')}>Pause</button>
            <button className="secondary-button" type="button" disabled={actionLoading || !currentId || currentStatus !== 'PAUSED'} onClick={() => currentId && runAction(() => resumeRollout(currentId), 'Rollout resumed.')}>Resume</button>
            <button className="ghost-button" type="button" disabled={actionLoading || !currentId || currentStatus === 'ROLLED_BACK'} onClick={() => currentId && runAction(() => rollbackRollout(currentId, { reason: 'Operator rollback from /rollout' }), 'Rollout rolled back to champion-only mode.')}>Rollback now</button>
          </div>
          {message ? <p>{message}</p> : null}
        </SectionCard>

        <div className="content-grid content-grid--two-columns">
          <SectionCard eyebrow="Guardrails" title="Guardrail summary" description="Triggered events and latest rollout recommendation.">
            {!current ? <p className="muted-text">No active rollout guardrails yet.</p> : (
              <>
                <p><strong>Latest recommendation:</strong> {latestDecision ? <span className={statusClass(latestDecision as RolloutDecisionCode)}>{latestDecision}</span> : 'No decision yet (insufficient sample is valid).'}</p>
                {!current.guardrail_events.length ? <p className="muted-text">No guardrail events triggered.</p> : (
                  <ul>
                    {current.guardrail_events.slice(0, 6).map((event) => (
                      <li key={event.id}><span className={statusClass(event.severity === 'CRITICAL' ? 'ROLLBACK_NOW' : 'EXTEND_CANARY')}>{event.code}</span> — {event.reason}</li>
                    ))}
                  </ul>
                )}
              </>
            )}
          </SectionCard>

          <SectionCard eyebrow="Recent runs" title="Rollout history" description="Status, distribution and summary for recent rollout runs.">
            {runs.length === 0 ? <EmptyState eyebrow="Rollout" title="No rollout runs yet" description="Create a rollout plan to promote a challenger gradually." /> : (
              <div className="table-wrapper">
                <table className="data-table">
                  <thead><tr><th>ID</th><th>Status</th><th>Mode</th><th>Canary %</th><th>Routed</th><th>Canary</th><th>Champion</th><th>Created</th><th>Summary</th></tr></thead>
                  <tbody>
                    {runs.slice(0, 12).map((run) => (
                      <tr key={run.id}>
                        <td>#{run.id}</td>
                        <td><span className={statusClass(run.status)}>{run.status}</span></td>
                        <td><span className={statusClass(run.plan.mode)}>{run.plan.mode}</span></td>
                        <td>{run.plan.canary_percentage}%</td>
                        <td>{run.routed_opportunities_count}</td>
                        <td>{run.canary_count}</td>
                        <td>{run.champion_count}</td>
                        <td>{new Date(run.created_at).toLocaleString()}</td>
                        <td>{run.summary}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </SectionCard>
        </div>
      </DataStateWrapper>
    </div>
  );
}

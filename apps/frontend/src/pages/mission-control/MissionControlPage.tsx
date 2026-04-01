import { useCallback, useEffect, useState } from 'react';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import {
  getAutonomousCycleExecutions,
  getAutonomousCycleOutcomes,
  getAutonomousCyclePlans,
  getAutonomousRuntimeRecommendations,
  getAutonomousRuntimeRuns,
  getAutonomousRuntimeSummary,
  getMissionControlStatus,
  runAutonomousRuntime,
} from '../../services/missionControl';
import type {
  AutonomousCycleExecution,
  AutonomousCycleOutcome,
  AutonomousCyclePlan,
  AutonomousRuntimeRecommendation,
  AutonomousRuntimeRun,
  AutonomousRuntimeSummary,
  MissionControlStatusResponse,
} from '../../types/missionControl';

export function MissionControlPage() {
  const [status, setStatus] = useState<MissionControlStatusResponse | null>(null);
  const [runs, setRuns] = useState<AutonomousRuntimeRun[]>([]);
  const [plans, setPlans] = useState<AutonomousCyclePlan[]>([]);
  const [executions, setExecutions] = useState<AutonomousCycleExecution[]>([]);
  const [outcomes, setOutcomes] = useState<AutonomousCycleOutcome[]>([]);
  const [recommendations, setRecommendations] = useState<AutonomousRuntimeRecommendation[]>([]);
  const [summary, setSummary] = useState<AutonomousRuntimeSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [s, r, p, e, o, rec, sum] = await Promise.all([
        getMissionControlStatus(),
        getAutonomousRuntimeRuns(),
        getAutonomousCyclePlans(),
        getAutonomousCycleExecutions(),
        getAutonomousCycleOutcomes(),
        getAutonomousRuntimeRecommendations(),
        getAutonomousRuntimeSummary(),
      ]);
      setStatus(s);
      setRuns(r);
      setPlans(p);
      setExecutions(e);
      setOutcomes(o);
      setRecommendations(rec);
      setSummary(sum);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load autonomous runtime loop.');
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
        title="Autonomous Runtime Loop"
        description="Continuous closed-cycle orchestration layer for paper-only operation: minimal human intervention, runtime-governed, no live execution."
        actions={<button type="button" className="primary-button" onClick={async () => { await runAutonomousRuntime({ cycle_count: 1 }); await load(); }}>Run autonomous runtime</button>}
      />

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Summary" title="Runtime loop counters" description="Auditable aggregate counters per autonomous runtime run.">
          <div className="system-metadata-grid">
            <div><strong>Cycles planned:</strong> {summary?.cycle_plan_count ?? 0}</div>
            <div><strong>Cycles executed:</strong> {summary?.cycle_execution_count ?? 0}</div>
            <div><strong>Blocked cycles:</strong> {runs[0]?.blocked_cycle_count ?? 0}</div>
            <div><strong>Dispatches:</strong> {summary?.totals.dispatch_count ?? 0}</div>
            <div><strong>Closed outcomes:</strong> {summary?.totals.closed_outcome_count ?? 0}</div>
            <div><strong>Postmortem handoffs:</strong> {summary?.totals.postmortem_handoff_count ?? 0}</div>
            <div><strong>Learning/reuse updates:</strong> {(summary?.totals.learning_handoff_count ?? 0) + (summary?.totals.reuse_applied_count ?? 0)}</div>
            <div><strong>Runtime mode:</strong> {status?.runtime.current_mode ?? 'unknown'}</div>
            <div><strong>Safety:</strong> {status?.safety.status ?? 'unknown'}</div>
          </div>
        </SectionCard>

        <SectionCard eyebrow="Cycle plans" title="Autonomous cycle plans" description="Per-cycle gating posture and planned steps.">
          <ul>{plans.slice(0, 6).map((p) => <li key={p.id}><StatusBadge tone="pending">{p.plan_status}</StatusBadge> mode={p.runtime_mode} portfolio={p.portfolio_posture} safety={p.safety_posture} steps={Object.keys(p.planned_step_flags).filter((k) => p.planned_step_flags[k]).join(', ')}</li>)}</ul>
        </SectionCard>

        <SectionCard eyebrow="Cycle execution" title="Execution trace" description="Executed/skipped/blocked steps with linkage to upstream/downstream runs.">
          <ul>{executions.slice(0, 6).map((e) => <li key={e.id}><StatusBadge tone="ready">{e.execution_status}</StatusBadge> executed=[{e.executed_steps.join(', ')}] skipped=[{e.skipped_steps.join(', ')}] blocked=[{e.blocked_steps.join(', ')}]</li>)}</ul>
        </SectionCard>

        <SectionCard eyebrow="Cycle outcomes" title="Outcome consolidation" description="Dispatch/watch/close/postmortem/learning counters per cycle.">
          <ul>{outcomes.slice(0, 6).map((o) => <li key={o.id}><StatusBadge tone="ready">{o.outcome_status}</StatusBadge> dispatch={o.dispatch_count} watch={o.watch_update_count} close={o.close_action_count} postmortem={o.postmortem_count} learning={o.learning_count} reuse={o.reuse_count}</li>)}</ul>
        </SectionCard>

        <SectionCard eyebrow="Recommendations" title="Runtime recommendations" description="Conservative explicit recommendation stream for each cycle run.">
          <ul>{recommendations.slice(0, 6).map((r) => <li key={r.id}><strong>{r.recommendation_type}</strong> — {r.rationale} blockers=[{r.blockers.join(', ')}] confidence={r.confidence}</li>)}</ul>
        </SectionCard>
      </DataStateWrapper>
    </div>
  );
}

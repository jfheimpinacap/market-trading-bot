import { useCallback, useEffect, useMemo, useState } from 'react';

import { EmptyState } from '../../components/EmptyState';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { navigate } from '../../lib/router';
import { getChaosBenchmarks, getChaosExperiments, getChaosRuns, getChaosSummary, runChaosExperiment } from '../../services/chaos';
import type { ChaosExperiment, ChaosRun, ResilienceBenchmark } from '../../types/chaos';

const statusTone = (status: string) => {
  if (status === 'SUCCESS' || status === 'RECOVERY_SUCCESS') return 'ready';
  if (status === 'RUNNING' || status === 'PARTIAL' || status === 'DEGRADED_MODE_TRIGGERED') return 'pending';
  if (status === 'FAILED' || status === 'ROLLBACK_TRIGGERED') return 'offline';
  return 'neutral';
};

const formatDate = (value: string | null) => {
  if (!value) return 'Pending';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short' }).format(date);
};

export function ChaosPage() {
  const [experiments, setExperiments] = useState<ChaosExperiment[]>([]);
  const [runs, setRuns] = useState<ChaosRun[]>([]);
  const [benchmarks, setBenchmarks] = useState<ResilienceBenchmark[]>([]);
  const [selectedExperimentId, setSelectedExperimentId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [exp, runData, benchData] = await Promise.all([getChaosExperiments(), getChaosRuns(), getChaosBenchmarks()]);
      setExperiments(exp);
      setRuns(runData);
      setBenchmarks(benchData);
      if (!selectedExperimentId && exp.length) {
        setSelectedExperimentId(exp[0].id);
      }
      await getChaosSummary();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load chaos lab data.');
    } finally {
      setLoading(false);
    }
  }, [selectedExperimentId]);

  useEffect(() => {
    void load();
  }, [load]);

  const latestBenchmark = useMemo(() => benchmarks[0] ?? null, [benchmarks]);

  const onRun = useCallback(async () => {
    if (!selectedExperimentId) return;
    setRunning(true);
    setError(null);
    setMessage(null);
    try {
      const result = await runChaosExperiment({ experiment_id: selectedExperimentId, trigger_mode: 'manual' });
      setMessage(`Chaos run #${result.id} finished with status ${result.status}.`);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not execute chaos run.');
    } finally {
      setRunning(false);
    }
  }, [load, selectedExperimentId]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Chaos lab / resilience benchmark"
        title="/chaos"
        description="Controlled fault injection and resilience validation for paper/demo-only operations. This layer is auditable, reversible, and never executes real money."
        actions={<div className="button-row"><button className="secondary-button" type="button" onClick={() => navigate('/incidents')}>Open Incidents</button><button className="secondary-button" type="button" onClick={() => navigate('/mission-control')}>Open Mission Control</button><button className="secondary-button" type="button" onClick={() => navigate('/runtime')}>Open Runtime</button><button className="secondary-button" type="button" onClick={() => navigate('/rollout')}>Open Rollout</button></div>}
      />

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Experiment catalog" title="Fault scenarios" description="Controlled experiments that inject reversible failures in key modules.">
          {!experiments.length ? (
            <EmptyState eyebrow="Chaos" title="No chaos experiments configured" description="Run backend seed/default setup to register baseline resilience scenarios." />
          ) : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Name</th><th>Type</th><th>Target module</th><th>Severity</th><th>Description</th></tr></thead>
                <tbody>
                  {experiments.map((experiment) => (
                    <tr key={experiment.id} style={{ cursor: 'pointer' }} onClick={() => setSelectedExperimentId(experiment.id)}>
                      <td>{experiment.name}</td>
                      <td>{experiment.experiment_type}</td>
                      <td>{experiment.target_module}</td>
                      <td><StatusBadge tone={statusTone(experiment.severity === 'critical' ? 'FAILED' : experiment.severity === 'high' ? 'PARTIAL' : 'SUCCESS')}>{experiment.severity.toUpperCase()}</StatusBadge></td>
                      <td>{experiment.description}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Run controls" title="Execute selected experiment" description="Manual trigger for scoped, reversible fault injection.">
          <div className="button-row">
            <label className="field-group">
              <span>Experiment</span>
              <select className="select-input" value={selectedExperimentId ?? undefined} onChange={(event) => setSelectedExperimentId(Number(event.target.value))}>
                {experiments.map((experiment) => <option key={experiment.id} value={experiment.id}>{experiment.name} ({experiment.target_module})</option>)}
              </select>
            </label>
            <button className="primary-button" type="button" disabled={running || !selectedExperimentId} onClick={() => void onRun()}>
              {running ? 'Running…' : 'Run resilience experiment'}
            </button>
          </div>
          {message ? <p>{message}</p> : null}
        </SectionCard>

        <div className="content-grid content-grid--two-columns">
          <SectionCard eyebrow="Benchmark panel" title="Latest resilience metrics" description="Detection, mitigation, recovery, degraded mode and rollback evidence.">
            {!latestBenchmark ? (
              <EmptyState eyebrow="Benchmark" title="No benchmark yet" description="Run a resilience experiment to validate degraded mode and recovery." />
            ) : (
              <div className="system-metadata-grid">
                <div><strong>Detection time:</strong> {latestBenchmark.detection_time_seconds ?? '—'}s</div>
                <div><strong>Mitigation time:</strong> {latestBenchmark.mitigation_time_seconds ?? '—'}s</div>
                <div><strong>Recovery time:</strong> {latestBenchmark.recovery_time_seconds ?? '—'}s</div>
                <div><strong>Incidents created:</strong> {latestBenchmark.incidents_created}</div>
                <div><strong>Alerts sent:</strong> {latestBenchmark.alerts_sent}</div>
                <div><strong>Queue items:</strong> {latestBenchmark.queue_items_created}</div>
                <div><strong>Resilience score:</strong> {latestBenchmark.resilience_score}</div>
                <div><strong>Recovery success rate:</strong> {latestBenchmark.recovery_success_rate}</div>
                <div><StatusBadge tone={statusTone(latestBenchmark.degraded_mode_triggered ? 'DEGRADED_MODE_TRIGGERED' : 'SUCCESS')}>DEGRADED_MODE_TRIGGERED: {latestBenchmark.degraded_mode_triggered ? 'YES' : 'NO'}</StatusBadge></div>
                <div><StatusBadge tone={statusTone(latestBenchmark.rollback_triggered ? 'ROLLBACK_TRIGGERED' : 'SUCCESS')}>ROLLBACK_TRIGGERED: {latestBenchmark.rollback_triggered ? 'YES' : 'NO'}</StatusBadge></div>
              </div>
            )}
          </SectionCard>

          <SectionCard eyebrow="Recent runs" title="Chaos run history" description="Auditable run trace with status and summary.">
            {!runs.length ? (
              <EmptyState eyebrow="Runs" title="No chaos runs yet" description="Run a resilience experiment to validate degraded mode and recovery." />
            ) : (
              <div className="table-wrapper">
                <table className="data-table">
                  <thead><tr><th>ID</th><th>Status</th><th>Experiment</th><th>Started</th><th>Finished</th><th>Summary</th></tr></thead>
                  <tbody>
                    {runs.slice(0, 12).map((run) => (
                      <tr key={run.id}>
                        <td>#{run.id}</td>
                        <td><StatusBadge tone={statusTone(run.status)}>{run.status}</StatusBadge></td>
                        <td>{run.experiment.name}</td>
                        <td>{formatDate(run.started_at)}</td>
                        <td>{formatDate(run.finished_at)}</td>
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

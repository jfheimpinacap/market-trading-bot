import { useCallback, useEffect, useState } from 'react';
import { EmptyState } from '../../components/EmptyState';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { navigate } from '../../lib/router';
import {
  getExperimentComparison,
  getExperimentRuns,
  getStrategyProfiles,
  runExperiment,
  seedExperimentProfiles,
} from '../../services/experiments';
import type { ExperimentComparison, ExperimentRun, ExperimentRunType, RunExperimentPayload, StrategyProfile } from '../../types/experiments';

function statusTone(value: string) {
  if (value === 'SUCCESS' || value === 'READY') return 'ready';
  if (value === 'RUNNING' || value === 'PARTIAL') return 'pending';
  if (value === 'FAILED') return 'offline';
  return 'neutral';
}

function formatDate(value: string | null) {
  if (!value) return 'Pending';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short' }).format(date);
}

function getErrorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

const runTypeOptions: ExperimentRunType[] = ['replay', 'live_eval', 'live_session_compare'];

const defaultForm: RunExperimentPayload = {
  strategy_profile_id: 0,
  run_type: 'replay',
  provider_scope: 'all',
  active_only: true,
  use_allocation: true,
  stop_on_error: false,
  execution_mode: 'naive',
  execution_profile: 'balanced_paper',
};

export function ExperimentsPage() {
  const [profiles, setProfiles] = useState<StrategyProfile[]>([]);
  const [runs, setRuns] = useState<ExperimentRun[]>([]);
  const [comparison, setComparison] = useState<ExperimentComparison | null>(null);
  const [selectedLeftRun, setSelectedLeftRun] = useState<number | null>(null);
  const [selectedRightRun, setSelectedRightRun] = useState<number | null>(null);
  const [form, setForm] = useState<RunExperimentPayload>(defaultForm);
  const [isLoading, setIsLoading] = useState(true);
  const [isRunning, setIsRunning] = useState(false);
  const [seedBusy, setSeedBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [profileResponse, runResponse] = await Promise.all([getStrategyProfiles(), getExperimentRuns()]);
      setProfiles(profileResponse);
      setRuns(runResponse);
      if (!form.strategy_profile_id && profileResponse.length) {
        setForm((prev) => ({ ...prev, strategy_profile_id: profileResponse[0].id }));
      }
      if (runResponse.length >= 2) {
        setSelectedLeftRun(runResponse[1].id);
        setSelectedRightRun(runResponse[0].id);
      }
    } catch (loadError) {
      setError(getErrorMessage(loadError, 'Could not load experiments data.'));
    } finally {
      setIsLoading(false);
    }
  }, [form.strategy_profile_id]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  async function runSelectedExperiment() {
    setIsRunning(true);
    setError(null);
    try {
      await runExperiment(form);
      await loadData();
    } catch (runError) {
      setError(getErrorMessage(runError, 'Could not execute experiment run.'));
    } finally {
      setIsRunning(false);
    }
  }

  async function loadComparison() {
    if (!selectedLeftRun || !selectedRightRun) return;
    setError(null);
    try {
      const response = await getExperimentComparison(selectedLeftRun, selectedRightRun);
      setComparison(response);
    } catch (comparisonError) {
      setError(getErrorMessage(comparisonError, 'Could not compare selected runs.'));
      setComparison(null);
    }
  }

  async function seedProfiles() {
    setSeedBusy(true);
    setError(null);
    try {
      await seedExperimentProfiles();
      await loadData();
    } catch (seedError) {
      setError(getErrorMessage(seedError, 'Could not seed profiles.'));
    } finally {
      setSeedBusy(false);
    }
  }

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Experiment runner / strategy profiles"
        title="Experiments"
        description="Compare strategy profiles across replay and live-paper evaluation in a local-first, paper/demo-only workflow. No real-money execution is enabled."
        actions={<div className="button-row"><button type="button" className="secondary-button" onClick={() => navigate('/replay')}>Open Replay</button><button type="button" className="secondary-button" onClick={() => navigate('/evaluation')}>Open Evaluation</button><button type="button" className="secondary-button" onClick={() => navigate('/readiness')}>Open Readiness</button><button type="button" className="secondary-button" disabled={seedBusy} onClick={() => void seedProfiles()}>{seedBusy ? 'Seeding…' : 'Seed base profiles'}</button></div>}
      />

      <DataStateWrapper isLoading={isLoading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        {!profiles.length ? (
          <EmptyState
            eyebrow="No strategy profiles"
            title="No strategy profiles available yet"
            description="Seed base profiles first to start replay-vs-live comparisons."
          />
        ) : (
          <>
            <SectionCard eyebrow="Profiles" title="Strategy profiles" description="Configurable operational profiles for repeatable comparisons.">
              <div className="table-wrapper">
                <table className="data-table">
                  <thead><tr><th>Name</th><th>Type</th><th>Scope</th><th>Status</th><th>Description</th></tr></thead>
                  <tbody>
                    {profiles.map((profile) => (
                      <tr key={profile.id}>
                        <td>{profile.name}</td>
                        <td>{profile.profile_type}</td>
                        <td>{profile.market_scope}</td>
                        <td><StatusBadge tone={profile.is_active ? 'ready' : 'offline'}>{profile.is_active ? 'ACTIVE' : 'DISABLED'}</StatusBadge></td>
                        <td>{profile.description}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </SectionCard>

            <SectionCard eyebrow="Run" title="Run experiment" description="Select profile and run type, then execute replay or live-paper comparison orchestration.">
              <div className="system-metadata-grid">
                <label>
                  Profile
                  <select value={form.strategy_profile_id} onChange={(event) => setForm((prev) => ({ ...prev, strategy_profile_id: Number(event.target.value) }))}>
                    {profiles.map((profile) => (
                      <option key={profile.id} value={profile.id}>{profile.name} ({profile.market_scope})</option>
                    ))}
                  </select>
                </label>
                <label>
                  Run type
                  <select value={form.run_type} onChange={(event) => setForm((prev) => ({ ...prev, run_type: event.target.value as ExperimentRunType }))}>
                    {runTypeOptions.map((option) => (
                      <option key={option} value={option}>{option}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Provider scope
                  <input value={form.provider_scope ?? 'all'} onChange={(event) => setForm((prev) => ({ ...prev, provider_scope: event.target.value }))} />
                </label>
                <label>
                  Related continuous session ID (optional)
                  <input type="number" onChange={(event) => setForm((prev) => ({ ...prev, related_continuous_session_id: event.target.value ? Number(event.target.value) : undefined }))} />
                </label>
                <label>
                  Execution mode
                  <select value={form.execution_mode} onChange={(event) => setForm((prev) => ({ ...prev, execution_mode: event.target.value as RunExperimentPayload['execution_mode'] }))}>
                    <option value="naive">naive</option>
                    <option value="execution_aware">execution_aware</option>
                  </select>
                </label>
                <label>
                  Execution profile
                  <select value={form.execution_profile} onChange={(event) => setForm((prev) => ({ ...prev, execution_profile: event.target.value as RunExperimentPayload['execution_profile'] }))}>
                    <option value="optimistic_paper">optimistic_paper</option>
                    <option value="balanced_paper">balanced_paper</option>
                    <option value="conservative_paper">conservative_paper</option>
                  </select>
                </label>
              </div>
              <div className="button-row" style={{ marginTop: '1rem' }}>
                <button type="button" className="primary-button" disabled={isRunning || !form.strategy_profile_id} onClick={() => void runSelectedExperiment()}>
                  {isRunning ? 'Running…' : 'Execute experiment'}
                </button>
              </div>
            </SectionCard>

            <SectionCard eyebrow="Runs" title="Recent experiment runs" description="Auditable run history across replay and live-paper evaluation.">
              {!runs.length ? (
                <EmptyState eyebrow="No experiment runs" title="No experiment runs yet." description="Run replay or evaluation first to compare strategy profiles." />
              ) : (
                <div className="table-wrapper">
                  <table className="data-table">
                    <thead><tr><th>ID</th><th>Status</th><th>Profile</th><th>Run type</th><th>Started</th><th>Finished</th><th>Summary</th></tr></thead>
                    <tbody>
                      {runs.map((run) => (
                        <tr key={run.id}>
                          <td>{run.id}</td>
                          <td><StatusBadge tone={statusTone(run.status)}>{run.status}</StatusBadge></td>
                          <td>{run.strategy_profile?.name}</td>
                          <td>{run.run_type}</td>
                          <td>{formatDate(run.started_at)}</td>
                          <td>{formatDate(run.finished_at)}</td>
                          <td>{run.summary || '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </SectionCard>

            <SectionCard eyebrow="Comparison" title="Run comparison" description="Compare two runs and inspect metric deltas side by side.">
              {runs.length < 2 ? (
                <EmptyState
                  eyebrow="Insufficient runs"
                  title="Run replay or evaluation first to compare strategy profiles."
                  description="At least two experiment runs are required for technical comparison."
                />
              ) : (
                <>
                  <div className="system-metadata-grid">
                    <label>
                      Left run
                      <select value={selectedLeftRun ?? undefined} onChange={(event) => setSelectedLeftRun(Number(event.target.value))}>
                        {runs.map((run) => <option key={run.id} value={run.id}>#{run.id} · {run.strategy_profile?.slug} · {run.run_type}</option>)}
                      </select>
                    </label>
                    <label>
                      Right run
                      <select value={selectedRightRun ?? undefined} onChange={(event) => setSelectedRightRun(Number(event.target.value))}>
                        {runs.map((run) => <option key={run.id} value={run.id}>#{run.id} · {run.strategy_profile?.slug} · {run.run_type}</option>)}
                      </select>
                    </label>
                  </div>
                  <div className="button-row" style={{ marginTop: '1rem' }}>
                    <button type="button" className="secondary-button" onClick={() => void loadComparison()}>Compare runs</button>
                  </div>
                  {comparison ? (
                    <>
                      <div className="table-wrapper" style={{ marginTop: '1rem' }}>
                        <table className="data-table">
                          <thead><tr><th>Metric</th><th>Left</th><th>Right</th><th>Delta (right-left)</th></tr></thead>
                          <tbody>
                            {Object.keys(comparison.delta).map((metric) => (
                              <tr key={metric}>
                                <td>{metric}</td>
                                <td>{String(comparison.left_run.metrics[metric] ?? '0')}</td>
                                <td>{String(comparison.right_run.metrics[metric] ?? '0')}</td>
                                <td>{comparison.delta[metric]}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                      <ul>
                        {comparison.interpretation.map((item) => <li key={item}>{item}</li>)}
                      </ul>
                      {comparison.execution_comparison ? (
                        <div className="system-metadata-grid">
                          <div><strong>Naive PnL:</strong> {comparison.execution_comparison.naive_total_pnl}</div>
                          <div><strong>Aware PnL:</strong> {comparison.execution_comparison.aware_total_pnl}</div>
                          <div><strong>Execution drag:</strong> {comparison.execution_comparison.execution_drag}</div>
                          <div><strong>Fill rate delta:</strong> {comparison.execution_comparison.fill_rate_delta}</div>
                          <div><strong>No-fill delta:</strong> {comparison.execution_comparison.no_fill_rate_delta}</div>
                        </div>
                      ) : null}
                    </>
                  ) : null}
                </>
              )}
            </SectionCard>
          </>
        )}
      </DataStateWrapper>
    </div>
  );
}

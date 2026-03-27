import { useCallback, useEffect, useMemo, useState } from 'react';
import { EmptyState } from '../../components/EmptyState';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { navigate } from '../../lib/router';
import {
  getReadinessProfiles,
  getReadinessSummary,
  runReadinessAssessment,
  seedReadinessProfiles,
} from '../../services/readiness';
import type { ReadinessAssessmentRun, ReadinessProfile, ReadinessSummary } from '../../types/readiness';

function getErrorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

function statusTone(value: string) {
  if (value === 'READY') return 'ready';
  if (value === 'CAUTION') return 'pending';
  if (value === 'NOT_READY') return 'offline';
  return 'neutral';
}

function formatDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short' }).format(date);
}

export function ReadinessPage() {
  const [profiles, setProfiles] = useState<ReadinessProfile[]>([]);
  const [selectedProfileId, setSelectedProfileId] = useState<number>(0);
  const [summary, setSummary] = useState<ReadinessSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRunning, setIsRunning] = useState(false);
  const [isSeeding, setIsSeeding] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [profileResponse, summaryResponse] = await Promise.all([getReadinessProfiles(), getReadinessSummary()]);
      setProfiles(profileResponse);
      setSummary(summaryResponse);
      if (!selectedProfileId && profileResponse.length) {
        setSelectedProfileId(profileResponse[0].id);
      }
    } catch (loadError) {
      setError(getErrorMessage(loadError, 'Could not load readiness data.'));
    } finally {
      setIsLoading(false);
    }
  }, [selectedProfileId]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const latestRun = summary?.latest_run ?? null;
  const failedGates = (latestRun?.details.gates ?? []).filter((gate) => !gate.passed);
  const recommendations = latestRun?.details.recommendations ?? [];
  const executionImpact = latestRun?.details.execution_impact_summary;

  const hasEvidence = useMemo(() => (summary?.total_runs ?? 0) > 0, [summary?.total_runs]);

  async function onRunAssessment() {
    if (!selectedProfileId) return;
    setIsRunning(true);
    setError(null);
    try {
      await runReadinessAssessment({ readiness_profile_id: selectedProfileId });
      await loadData();
    } catch (runError) {
      setError(getErrorMessage(runError, 'Could not run readiness assessment.'));
    } finally {
      setIsRunning(false);
    }
  }

  async function onSeedProfiles() {
    setIsSeeding(true);
    setError(null);
    try {
      await seedReadinessProfiles();
      await loadData();
    } catch (seedError) {
      setError(getErrorMessage(seedError, 'Could not seed readiness profiles.'));
    } finally {
      setIsSeeding(false);
    }
  }

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Go-live readiness / promotion gates"
        title="Readiness"
        description="Formal readiness assessment for promotion gates. This does NOT enable real money and remains paper/demo only."
        actions={<div className="button-row"><button type="button" className="secondary-button" onClick={() => navigate('/evaluation')}>Open Evaluation</button><button type="button" className="secondary-button" onClick={() => navigate('/experiments')}>Open Experiments</button><button type="button" className="secondary-button" onClick={() => navigate('/runtime')}>Open Runtime</button><button type="button" className="secondary-button" disabled={isSeeding} onClick={() => void onSeedProfiles()}>{isSeeding ? 'Seeding…' : 'Seed base profiles'}</button></div>}
      />

      <DataStateWrapper isLoading={isLoading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        {!profiles.length ? (
          <EmptyState eyebrow="No readiness profiles" title="Seed readiness profiles first" description="Create conservative/balanced/strict profiles before running assessments." />
        ) : (
          <>
            <SectionCard eyebrow="Profiles" title="Readiness profiles" description={'Profiles define what "ready" means with auditable gate thresholds.'}>
              <div className="table-wrapper">
                <table className="data-table">
                  <thead><tr><th>Name</th><th>Type</th><th>Status</th><th>Description</th></tr></thead>
                  <tbody>
                    {profiles.map((profile) => (
                      <tr key={profile.id}>
                        <td>{profile.name}</td>
                        <td>{profile.profile_type}</td>
                        <td><StatusBadge tone={profile.is_active ? 'ready' : 'offline'}>{profile.is_active ? 'ACTIVE' : 'DISABLED'}</StatusBadge></td>
                        <td>{profile.description}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </SectionCard>

            <SectionCard eyebrow="Run assessment" title="Execute readiness assessment" description="Run a formal gate check against evaluation/replay/experiment/safety/operator evidence.">
              <div className="system-metadata-grid">
                <label>
                  Profile
                  <select value={selectedProfileId} onChange={(event) => setSelectedProfileId(Number(event.target.value))}>
                    {profiles.map((profile) => <option key={profile.id} value={profile.id}>{profile.name}</option>)}
                  </select>
                </label>
              </div>
              <div className="button-row" style={{ marginTop: '1rem' }}>
                <button type="button" className="primary-button" disabled={isRunning || !selectedProfileId} onClick={() => void onRunAssessment()}>
                  {isRunning ? 'Assessing…' : 'Run readiness assessment'}
                </button>
              </div>
            </SectionCard>

            {!hasEvidence || !latestRun ? (
              <EmptyState
                eyebrow="No readiness assessments yet"
                title="Run evaluation and replay first to assess readiness."
                description="No readiness assessments yet. Build evaluation/replay/experiment evidence and run a readiness assessment."
              />
            ) : (
              <>
                <SectionCard eyebrow="Current summary" title="Latest readiness decision" description="Transparent status with pass/fail gates and recommendations.">
                  <div className="system-metadata-grid">
                    <div><strong>Status:</strong> <StatusBadge tone={statusTone(latestRun.status)}>{latestRun.status}</StatusBadge></div>
                    <div><strong>Profile:</strong> {latestRun.readiness_profile.name}</div>
                    <div><strong>Overall score:</strong> {latestRun.overall_score ?? 'N/A'}</div>
                    <div><strong>Gates passed:</strong> {latestRun.gates_passed_count}</div>
                    <div><strong>Gates failed:</strong> {latestRun.gates_failed_count}</div>
                    <div><strong>Warnings:</strong> {latestRun.warnings_count}</div>
                    <div><strong>Created:</strong> {formatDate(latestRun.created_at)}</div>
                  </div>
                  <p style={{ marginTop: '1rem' }}>{latestRun.summary}</p>
                  {recommendations.length ? (
                    <>
                      <h4>Recommendations</h4>
                      <ul>{recommendations.map((item) => <li key={item}>{item}</li>)}</ul>
                    </>
                  ) : null}
                </SectionCard>

                {failedGates.length ? (
                  <SectionCard eyebrow="Failed gates" title="Promotion blockers" description="Each failed gate includes expected threshold, observed value, and reason.">
                    <div className="table-wrapper">
                      <table className="data-table">
                        <thead><tr><th>Gate</th><th>Expected</th><th>Actual</th><th>Reason</th></tr></thead>
                        <tbody>
                          {failedGates.map((gate) => (
                            <tr key={gate.gate}>
                              <td>{gate.gate}</td>
                              <td>{gate.comparator} {gate.expected}</td>
                              <td>{gate.actual}</td>
                              <td>{gate.reason}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </SectionCard>
                ) : null}

                <SectionCard eyebrow="Execution realism impact" title="Readiness penalty from execution quality" description="Readiness score now accounts for execution-aware replay realism.">
                  {executionImpact ? (
                    <div className="system-metadata-grid">
                      <div><strong>Execution-aware runs:</strong> {executionImpact.execution_aware_runs}</div>
                      <div><strong>Avg fill rate:</strong> {(executionImpact.avg_fill_rate * 100).toFixed(2)}%</div>
                      <div><strong>Avg no-fill rate:</strong> {(executionImpact.avg_no_fill_rate * 100).toFixed(2)}%</div>
                      <div><strong>Avg execution drag:</strong> {executionImpact.avg_execution_drag}</div>
                      <div><strong>Realism score:</strong> {(executionImpact.avg_execution_realism_score * 100).toFixed(2)}%</div>
                      <div><strong>Readiness penalty:</strong> {(executionImpact.readiness_penalty * 100).toFixed(2)}%</div>
                    </div>
                  ) : (
                    <p>Run replay with execution-aware mode to measure fill realism.</p>
                  )}
                </SectionCard>
              </>
            )}

            <SectionCard eyebrow="History" title="Recent readiness runs" description="Auditable history of readiness decisions.">
              {!(summary?.recent_runs?.length) ? (
                <EmptyState eyebrow="No history" title="No readiness assessments yet." description="Run a readiness assessment to create auditable history." />
              ) : (
                <div className="table-wrapper">
                  <table className="data-table">
                    <thead><tr><th>ID</th><th>Status</th><th>Profile</th><th>Created</th><th>Summary</th></tr></thead>
                    <tbody>
                      {summary?.recent_runs.map((run: ReadinessAssessmentRun) => (
                        <tr key={run.id}>
                          <td>{run.id}</td>
                          <td><StatusBadge tone={statusTone(run.status)}>{run.status}</StatusBadge></td>
                          <td>{run.readiness_profile.name}</td>
                          <td>{formatDate(run.created_at)}</td>
                          <td>{run.summary || '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </SectionCard>
          </>
        )}
      </DataStateWrapper>
    </div>
  );
}

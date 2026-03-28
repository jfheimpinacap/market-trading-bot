import { useCallback, useEffect, useMemo, useState } from 'react';

import { EmptyState } from '../../components/EmptyState';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { navigate } from '../../lib/router';
import { getPolicyTuningCandidates } from '../../services/policyTuning';
import { evaluatePolicyRollout, getPolicyRolloutRuns, getPolicyRolloutSummary, rollbackPolicyRollout, startPolicyRollout } from '../../services/policyRollout';
import type { PolicyRolloutRecommendationCode, PolicyRolloutStatus } from '../../types/policyRollout';

const formatDate = (value: string | null | undefined) => (value ? new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) : '—');

function statusTone(status: PolicyRolloutStatus): 'ready' | 'pending' | 'offline' | 'neutral' {
  if (status === 'STABLE' || status === 'COMPLETED') return 'ready';
  if (status === 'ROLLBACK_RECOMMENDED' || status === 'ABORTED') return 'offline';
  if (status === 'OBSERVING' || status === 'CAUTION') return 'pending';
  return 'neutral';
}

function recommendationTone(code: PolicyRolloutRecommendationCode): 'ready' | 'pending' | 'offline' | 'neutral' {
  if (code === 'KEEP_CHANGE') return 'ready';
  if (code === 'ROLLBACK_CHANGE') return 'offline';
  if (code === 'REQUIRE_MORE_DATA' || code === 'STABILIZE_AND_MONITOR') return 'pending';
  return 'neutral';
}

export function PolicyRolloutPage() {
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [summary, setSummary] = useState<Awaited<ReturnType<typeof getPolicyRolloutSummary>> | null>(null);
  const [runs, setRuns] = useState<Awaited<ReturnType<typeof getPolicyRolloutRuns>>>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryPayload, runsPayload] = await Promise.all([getPolicyRolloutSummary(), getPolicyRolloutRuns()]);
      setSummary(summaryPayload);
      setRuns(runsPayload);
      setSelectedId((curr) => curr ?? runsPayload[0]?.id ?? null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Could not load policy rollout monitor.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const selected = useMemo(() => runs.find((run) => run.id === selectedId) ?? null, [runs, selectedId]);
  const activeRun = useMemo(() => runs.find((run) => run.rollout_status === 'OBSERVING') ?? runs[0] ?? null, [runs]);
  const latestRecommendation = selected?.recommendations[0] ?? null;

  const startFromLatestAppliedCandidate = useCallback(async () => {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const candidates = await getPolicyTuningCandidates();
      const candidate = candidates.find((item) => item.status === 'APPLIED');
      if (!candidate) {
        setError('No applied policy tuning candidate found. Apply a candidate in /policy-tuning first.');
        return;
      }
      await startPolicyRollout({ policy_tuning_candidate_id: candidate.id, observation_window_days: 14, metadata: { started_from: '/policy-rollout' } });
      setMessage(`Rollout monitor started for candidate #${candidate.id}.`);
      await load();
    } catch (startError) {
      setError(startError instanceof Error ? startError.message : 'Could not start policy rollout monitor.');
    } finally {
      setBusy(false);
    }
  }, [load]);

  const evaluateSelected = useCallback(async () => {
    if (!selected) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const response = await evaluatePolicyRollout(selected.id, { metadata: { triggered_from: '/policy-rollout' } });
      setMessage(`Evaluation complete for run #${selected.id}: ${response.recommendation}.`);
      await load();
    } catch (evaluateError) {
      setError(evaluateError instanceof Error ? evaluateError.message : 'Could not evaluate rollout run.');
    } finally {
      setBusy(false);
    }
  }, [load, selected]);

  const rollbackSelected = useCallback(async () => {
    if (!selected) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await rollbackPolicyRollout(selected.id, { reason: 'Manual rollback requested from policy rollout monitor.', require_approval: true });
      setMessage(`Rollback applied for run #${selected.id}. Candidate marked as rolled back/superseded.`);
      await load();
    } catch (rollbackError) {
      setError(rollbackError instanceof Error ? rollbackError.message : 'Could not rollback rollout run.');
    } finally {
      setBusy(false);
    }
  }, [load, selected]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Post-change policy monitoring"
        title="/policy-rollout"
        description="Manual-first rollout guard for applied policy tuning changes. Captures baseline vs post-change behavior, recommends keep/observe/rollback, and supports auditable manual rollback only."
        actions={<div className="button-row"><button type="button" className="primary-button" disabled={busy} onClick={() => void startFromLatestAppliedCandidate()}>Start rollout monitor</button><button type="button" className="secondary-button" onClick={() => navigate('/policy-tuning')}>Policy tuning</button><button type="button" className="secondary-button" onClick={() => navigate('/trust-calibration')}>Trust calibration</button><button type="button" className="ghost-button" onClick={() => navigate('/trace')}>Trace explorer</button></div>}
      />

      {message ? <p className="success-text">{message}</p> : null}

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Manual-first guardrail" title="No automatic rollback" description="Policy rollout emits recommendation-first outcomes and requires explicit human action for rollback.">
          <div className="cockpit-metric-grid">
            <div><strong>Total runs</strong><div>{summary?.total_runs ?? 0}</div></div>
            <div><strong>Observing</strong><div>{summary?.observing_runs ?? 0}</div></div>
            <div><strong>Stable</strong><div>{summary?.stable_runs ?? 0}</div></div>
            <div><strong>Rollback recommended</strong><div>{summary?.rollback_recommended_runs ?? 0}</div></div>
          </div>
        </SectionCard>

        {runs.length === 0 ? <EmptyState eyebrow="Policy rollout" title="No rollout runs yet" description="Start a rollout monitor from an applied policy tuning change." /> : null}

        <div className="content-grid content-grid--two-columns">
          <SectionCard eyebrow="Active rollout" title={activeRun ? `Run #${activeRun.id}` : 'No active rollout'} description="Current candidate under observation and its latest recommendation.">
            {!activeRun ? <p className="muted-text">No active observation run right now.</p> : (
              <ul className="key-value-list">
                <li><span>Candidate</span><strong>#{activeRun.policy_tuning_candidate}</strong></li>
                <li><span>Status</span><strong><StatusBadge tone={statusTone(activeRun.rollout_status)}>{activeRun.rollout_status}</StatusBadge></strong></li>
                <li><span>Observation window</span><strong>{activeRun.observation_window_days} days</strong></li>
                <li><span>Current recommendation</span><strong>{activeRun.recommendations[0] ? <StatusBadge tone={recommendationTone(activeRun.recommendations[0].recommendation)}>{activeRun.recommendations[0].recommendation}</StatusBadge> : 'Not evaluated yet'}</strong></li>
                <li><span>Summary</span><strong>{activeRun.summary || '—'}</strong></li>
              </ul>
            )}
          </SectionCard>

          <SectionCard eyebrow="Recommendation" title={latestRecommendation ? latestRecommendation.recommendation : 'Evaluate run'} description="Recommendation-first outcome with rationale, reason codes, and evidence links.">
            {!selected ? <p className="muted-text">Select a run to inspect recommendation details.</p> : latestRecommendation ? (
              <div className="page-stack">
                <p>{latestRecommendation.rationale}</p>
                <ul className="key-value-list">
                  <li><span>Reason codes</span><strong>{latestRecommendation.reason_codes.join(', ') || '—'}</strong></li>
                  <li><span>Confidence</span><strong>{latestRecommendation.confidence}</strong></li>
                  <li><span>Warnings</span><strong>{latestRecommendation.warnings.join(' | ') || '—'}</strong></li>
                </ul>
                <div className="button-row">
                  <button type="button" className="link-button" onClick={() => navigate(`/trace?root_type=policy_rollout_run&root_id=${selected.id}`)}>Open rollout trace</button>
                  <button type="button" className="link-button" onClick={() => navigate('/incidents')}>Open incidents</button>
                  <button type="button" className="link-button" onClick={() => navigate('/approvals')}>Open approvals</button>
                </div>
              </div>
            ) : <p className="muted-text">No recommendation yet. Evaluate post-change metrics to compute deltas.</p>}
          </SectionCard>
        </div>

        <SectionCard eyebrow="Baseline vs post-change" title={selected ? `Run #${selected.id} metrics` : 'Select a run'} description="Before/after metrics and deltas for approvals, friction, incidents, and manual intervention.">
          {!selected ? <EmptyState eyebrow="Run detail" title="Select a rollout run" description="Pick one run to compare baseline and post-change snapshots." /> : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Metric</th><th>Baseline</th><th>Post-change</th><th>Delta</th></tr></thead>
                <tbody>
                  {['approval_rate', 'rejection_rate', 'approval_friction_score', 'auto_execution_success_rate', 'manual_intervention_rate', 'auto_action_followed_by_incident_rate'].map((metric) => (
                    <tr key={metric}>
                      <td>{metric}</td>
                      <td>{String(selected.baseline_snapshot?.metrics?.[metric] ?? '0')}</td>
                      <td>{String(selected.post_change_snapshot?.metrics?.[metric] ?? '—')}</td>
                      <td>{String(selected.post_change_snapshot?.deltas?.[metric] ?? '—')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <div className="button-row">
            <button type="button" className="secondary-button" disabled={busy || !selected} onClick={() => void evaluateSelected()}>Evaluate selected run</button>
          </div>
        </SectionCard>

        <SectionCard eyebrow="Rollback" title="Manual rollback assisted loop" description="Rollback requires explicit operator confirmation and stays fully auditable.">
          {!selected ? <p className="muted-text">Select a run to enable rollback controls.</p> : (
            <div className="page-stack">
              <ul className="key-value-list">
                <li><span>Candidate</span><strong>#{selected.policy_tuning_candidate}</strong></li>
                <li><span>Current status</span><strong>{selected.rollout_status}</strong></li>
                <li><span>Last summary</span><strong>{selected.summary || '—'}</strong></li>
              </ul>
              <div className="button-row">
                <button type="button" className="primary-button" disabled={busy} onClick={() => void rollbackSelected()}>Apply manual rollback</button>
                <button type="button" className="ghost-button" onClick={() => navigate('/approvals')}>Open approval center</button>
              </div>
            </div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Recent runs" title="Policy rollout history" description="Auditable timeline of monitoring runs and final outcomes.">
          {runs.length === 0 ? <p className="muted-text">No rollout history yet.</p> : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Created</th><th>Candidate</th><th>Status</th><th>Recommendation</th><th>Summary</th></tr></thead>
                <tbody>
                  {runs.map((run) => (
                    <tr key={run.id} className={selectedId === run.id ? 'is-selected-row' : ''} onClick={() => setSelectedId(run.id)}>
                      <td>{formatDate(run.created_at)}</td>
                      <td>#{run.policy_tuning_candidate}</td>
                      <td><StatusBadge tone={statusTone(run.rollout_status)}>{run.rollout_status}</StatusBadge></td>
                      <td>{run.recommendations[0] ? <StatusBadge tone={recommendationTone(run.recommendations[0].recommendation)}>{run.recommendations[0].recommendation}</StatusBadge> : '—'}</td>
                      <td>{run.summary || '—'}</td>
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

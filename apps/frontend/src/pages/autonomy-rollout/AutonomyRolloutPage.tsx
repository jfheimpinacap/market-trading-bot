import { useCallback, useEffect, useMemo, useState } from 'react';

import { EmptyState } from '../../components/EmptyState';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { navigate } from '../../lib/router';
import { getAutonomyRecommendations } from '../../services/autonomy';
import { evaluateAutonomyRollout, getAutonomyRolloutRuns, getAutonomyRolloutSummary, rollbackAutonomyRollout, startAutonomyRollout } from '../../services/autonomyRollout';
import type { AutonomyRolloutRecommendationCode, AutonomyRolloutStatus } from '../../types/autonomyRollout';

const formatDate = (value: string | null | undefined) => (value ? new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) : '—');

function statusTone(status: AutonomyRolloutStatus): 'ready' | 'pending' | 'offline' | 'neutral' {
  if (status === 'STABLE' || status === 'COMPLETED') return 'ready';
  if (status === 'FREEZE_RECOMMENDED' || status === 'ROLLBACK_RECOMMENDED' || status === 'ABORTED') return 'offline';
  if (status === 'OBSERVING' || status === 'CAUTION') return 'pending';
  return 'neutral';
}

function recommendationTone(code: AutonomyRolloutRecommendationCode): 'ready' | 'pending' | 'offline' | 'neutral' {
  if (code === 'KEEP_STAGE') return 'ready';
  if (code === 'FREEZE_DOMAIN' || code === 'ROLLBACK_STAGE') return 'offline';
  if (code === 'REQUIRE_MORE_DATA' || code === 'STABILIZE_AND_MONITOR') return 'pending';
  return 'neutral';
}

export function AutonomyRolloutPage() {
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [summary, setSummary] = useState<Awaited<ReturnType<typeof getAutonomyRolloutSummary>> | null>(null);
  const [runs, setRuns] = useState<Awaited<ReturnType<typeof getAutonomyRolloutRuns>>>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryPayload, runsPayload] = await Promise.all([getAutonomyRolloutSummary(), getAutonomyRolloutRuns()]);
      setSummary(summaryPayload);
      setRuns(runsPayload);
      setSelectedId((curr) => curr ?? runsPayload[0]?.id ?? null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Could not load autonomy rollout monitor.');
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

  const startFromLatestAppliedTransition = useCallback(async () => {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const recommendations = await getAutonomyRecommendations();
      const transition = recommendations.find((item) => item.transition?.status === 'APPLIED')?.transition;
      if (!transition) {
        setError('No APPLIED autonomy transition found. Apply one in /autonomy first.');
        return;
      }
      await startAutonomyRollout({ autonomy_stage_transition_id: transition.id, observation_window_days: 14, metadata: { started_from: '/autonomy-rollout' } });
      setMessage(`Autonomy rollout monitor started for transition #${transition.id}.`);
      await load();
    } catch (startError) {
      setError(startError instanceof Error ? startError.message : 'Could not start autonomy rollout monitor.');
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
      const response = await evaluateAutonomyRollout(selected.id, { metadata: { triggered_from: '/autonomy-rollout' } });
      setMessage(`Evaluation complete for run #${selected.id}: ${response.recommendation}.`);
      await load();
    } catch (evaluateError) {
      setError(evaluateError instanceof Error ? evaluateError.message : 'Could not evaluate autonomy rollout run.');
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
      await rollbackAutonomyRollout(selected.id, { reason: 'Manual rollback requested from autonomy rollout monitor.', require_approval: true });
      setMessage(`Manual rollback applied for run #${selected.id}.`);
      await load();
    } catch (rollbackError) {
      setError(rollbackError instanceof Error ? rollbackError.message : 'Could not rollback autonomy rollout run.');
    } finally {
      setBusy(false);
    }
  }, [load, selected]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Domain transition baselining"
        title="/autonomy-rollout"
        description="Manual-first post-change monitor for autonomy stage transitions. Compares baseline vs post-change snapshots, emits recommendation-first outcomes, and keeps rollback explicit and auditable."
        actions={<div className="button-row"><button type="button" className="primary-button" disabled={busy} onClick={() => void startFromLatestAppliedTransition()}>Start rollout monitor</button><button type="button" className="secondary-button" onClick={() => navigate('/autonomy')}>Autonomy</button><button type="button" className="secondary-button" onClick={() => navigate('/cockpit')}>Cockpit</button><button type="button" className="ghost-button" onClick={() => navigate('/trace')}>Trace explorer</button></div>}
      />
      {message ? <p className="success-text">{message}</p> : null}
      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Observation board" title="Cross-domain rollback loop" description="Recommendation-first monitoring for domain transitions. REQUIRE_MORE_DATA is a healthy stabilization state.">
          <div className="cockpit-metric-grid">
            <div><strong>Total runs</strong><div>{summary?.total_runs ?? 0}</div></div>
            <div><strong>Observing</strong><div>{summary?.observing_runs ?? 0}</div></div>
            <div><strong>Freeze recommended</strong><div>{summary?.freeze_recommended_runs ?? 0}</div></div>
            <div><strong>Rollback recommended</strong><div>{summary?.rollback_recommended_runs ?? 0}</div></div>
          </div>
        </SectionCard>

        {runs.length === 0 ? <EmptyState eyebrow="Autonomy rollout" title="No rollout runs yet" description="Start an autonomy rollout monitor from an applied domain transition." /> : null}

        <div className="content-grid content-grid--two-columns">
          <SectionCard eyebrow="Active rollout" title={activeRun ? `Run #${activeRun.id}` : 'No active rollout'} description="Domain under observation with current recommendation.">
            {!activeRun ? <p className="muted-text">No active observation run right now.</p> : (
              <ul className="key-value-list">
                <li><span>Transition</span><strong>#{activeRun.autonomy_stage_transition}</strong></li>
                <li><span>Status</span><strong><StatusBadge tone={statusTone(activeRun.rollout_status)}>{activeRun.rollout_status}</StatusBadge></strong></li>
                <li><span>Current stage</span><strong>{String(activeRun.metadata?.applied_stage ?? '—')}</strong></li>
                <li><span>Previous stage</span><strong>{String(activeRun.metadata?.previous_stage ?? '—')}</strong></li>
                <li><span>Recommendation</span><strong>{activeRun.recommendations[0] ? <StatusBadge tone={recommendationTone(activeRun.recommendations[0].recommendation)}>{activeRun.recommendations[0].recommendation}</StatusBadge> : 'Not evaluated yet'}</strong></li>
              </ul>
            )}
          </SectionCard>

          <SectionCard eyebrow="Recommendation" title={latestRecommendation ? latestRecommendation.recommendation : 'Evaluate run'} description="Keep/freeze/rollback recommendation with rationale and evidence links.">
            {!selected ? <p className="muted-text">Select a run to inspect recommendation details.</p> : latestRecommendation ? (
              <div className="page-stack">
                <p>{latestRecommendation.rationale}</p>
                <ul className="key-value-list">
                  <li><span>Reason codes</span><strong>{latestRecommendation.reason_codes.join(', ') || '—'}</strong></li>
                  <li><span>Confidence</span><strong>{latestRecommendation.confidence}</strong></li>
                  <li><span>Warnings</span><strong>{latestRecommendation.warnings.join(' | ') || '—'}</strong></li>
                  <li><span>Cross-domain notes</span><strong>{latestRecommendation.cross_domain_notes.length > 0 ? 'Present' : 'None'}</strong></li>
                </ul>
                <div className="button-row">
                  <button type="button" className="link-button" onClick={() => navigate(`/trace?root_type=autonomy_rollout_run&root_id=${selected.id}`)}>Open rollout trace</button>
                  <button type="button" className="link-button" onClick={() => navigate('/incidents')}>Incidents</button>
                  <button type="button" className="link-button" onClick={() => navigate('/approvals')}>Approvals</button>
                </div>
              </div>
            ) : <p className="muted-text">No recommendation yet. Evaluate post-change metrics first.</p>}
          </SectionCard>
        </div>

        <SectionCard eyebrow="Baseline vs post-change" title={selected ? `Run #${selected.id} metrics` : 'Select a run'} description="Before/after deltas for friction, incidents, blocked and degraded context signals.">
          {!selected ? <EmptyState eyebrow="Run detail" title="Select a rollout run" description="Pick one run to compare baseline and post-change snapshots." /> : (
            <div className="table-wrapper"><table className="data-table"><thead><tr><th>Metric</th><th>Baseline</th><th>Post-change</th><th>Delta</th></tr></thead><tbody>
              {['approval_rate', 'approval_friction_score', 'auto_execution_success_rate', 'incident_after_auto_rate', 'blocked_rate', 'degraded_context_rate'].map((metric) => (
                <tr key={metric}><td>{metric}</td><td>{String(selected.baseline_snapshot?.metrics?.[metric] ?? '0')}</td><td>{String(selected.post_change_snapshot?.metrics?.[metric] ?? '—')}</td><td>{String(selected.post_change_snapshot?.deltas?.[metric] ?? '—')}</td></tr>
              ))}
            </tbody></table></div>
          )}
          <div className="button-row"><button type="button" className="secondary-button" disabled={busy || !selected} onClick={() => void evaluateSelected()}>Evaluate selected run</button></div>
        </SectionCard>

        <SectionCard eyebrow="Rollback" title="Manual rollback assisted" description="Rollback is explicit, auditable, and optionally approval-gated for high-impact domains.">
          {!selected ? <p className="muted-text">Select a run to enable rollback controls.</p> : (
            <div className="button-row"><button type="button" className="primary-button" disabled={busy} onClick={() => void rollbackSelected()}>Apply manual rollback</button><button type="button" className="ghost-button" onClick={() => navigate('/approvals')}>Open approval center</button></div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Recent runs" title="Autonomy rollout history" description="Auditable timeline of domain rollout runs and outcomes.">
          {runs.length === 0 ? <p className="muted-text">No rollout history yet.</p> : (
            <div className="table-wrapper"><table className="data-table"><thead><tr><th>Created</th><th>Domain</th><th>Status</th><th>Recommendation</th><th>Summary</th></tr></thead><tbody>
              {runs.map((run) => (<tr key={run.id} className={selectedId === run.id ? 'is-selected-row' : ''} onClick={() => setSelectedId(run.id)}><td>{formatDate(run.created_at)}</td><td>#{run.domain}</td><td><StatusBadge tone={statusTone(run.rollout_status)}>{run.rollout_status}</StatusBadge></td><td>{run.recommendations[0] ? <StatusBadge tone={recommendationTone(run.recommendations[0].recommendation)}>{run.recommendations[0].recommendation}</StatusBadge> : '—'}</td><td>{run.summary || '—'}</td></tr>))}
            </tbody></table></div>
          )}
        </SectionCard>
      </DataStateWrapper>
    </div>
  );
}

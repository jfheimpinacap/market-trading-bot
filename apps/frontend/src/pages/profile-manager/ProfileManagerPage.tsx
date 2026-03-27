import { useCallback, useEffect, useMemo, useState } from 'react';

import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { navigate } from '../../lib/router';
import { applyProfileDecision, getCurrentProfileGovernance, getProfileGovernanceRuns, getProfileGovernanceSummary, runProfileGovernance } from '../../services/profileManager';
import type { ProfileGovernanceRun, ProfileGovernanceSummary } from '../../types/profileManager';

const badgeClass = (state: string) => {
  if (state === 'NORMAL') return 'signal-badge signal-badge--actionable';
  if (state === 'CAUTION') return 'signal-badge signal-badge--monitor';
  if (state === 'STRESSED' || state === 'CONCENTRATED' || state === 'DRAWDOWN_MODE') return 'signal-badge signal-badge--bearish';
  if (state === 'DEFENSIVE' || state === 'BLOCKED') return 'signal-badge signal-badge--bearish';
  if (state === 'APPLY_SAFE') return 'signal-badge signal-badge--monitor';
  if (state === 'RECOMMEND_ONLY') return 'signal-badge signal-badge--neutral';
  return 'signal-badge signal-badge--neutral';
};

export function ProfileManagerPage() {
  const [summary, setSummary] = useState<ProfileGovernanceSummary | null>(null);
  const [current, setCurrent] = useState<ProfileGovernanceRun | null>(null);
  const [runs, setRuns] = useState<ProfileGovernanceRun[]>([]);
  const [decisionMode, setDecisionMode] = useState('RECOMMEND_ONLY');
  const [running, setRunning] = useState(false);
  const [applying, setApplying] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [s, r, c] = await Promise.allSettled([getProfileGovernanceSummary(), getProfileGovernanceRuns(), getCurrentProfileGovernance()]);
      if (s.status === 'fulfilled') setSummary(s.value);
      if (r.status === 'fulfilled') setRuns(r.value);
      if (c.status === 'fulfilled') setCurrent(c.value);
      if (s.status === 'rejected') throw s.reason;
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load profile governance state.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const onRun = useCallback(async () => {
    setRunning(true);
    setMessage(null);
    try {
      const run = await runProfileGovernance({ decision_mode: decisionMode, triggered_by: 'frontend_ui' });
      setMessage(`Profile governance run #${run.id} completed (${run.regime}).`);
      await load();
    } catch (e) {
      setMessage(e instanceof Error ? e.message : 'Run failed.');
    } finally {
      setRunning(false);
    }
  }, [decisionMode, load]);

  const onApply = useCallback(async () => {
    if (!current?.decision?.id) return;
    setApplying(true);
    setMessage(null);
    try {
      await applyProfileDecision(current.decision.id);
      setMessage(`Decision #${current.decision.id} applied.`);
      await load();
    } catch (e) {
      setMessage(e instanceof Error ? e.message : 'Apply failed.');
    } finally {
      setApplying(false);
    }
  }, [current, load]);

  const cards = useMemo(() => [
    { label: 'Current regime', value: summary?.current_regime ?? 'UNKNOWN', badge: true },
    { label: 'Decision mode', value: current?.decision?.decision_mode ?? summary?.decision_mode ?? 'N/A', badge: true },
    { label: 'Runtime', value: summary?.runtime_mode ?? 'UNKNOWN' },
    { label: 'Readiness', value: summary?.readiness_status ?? 'UNKNOWN' },
    { label: 'Safety', value: summary?.safety_status ?? 'UNKNOWN' },
    { label: 'Applied', value: current?.decision?.is_applied ? 'YES' : 'NO' },
  ], [summary, current]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Adaptive profile manager"
        title="/profile-manager"
        description="Auditable meta-governance layer: classifies operational regime and coordinates module profiles for paper/demo only. No real-money execution."
        actions={<div className="button-row"><button className="secondary-button" type="button" onClick={() => navigate('/portfolio-governor')}>Open Portfolio Governor</button><button className="secondary-button" type="button" onClick={() => navigate('/mission-control')}>Open Mission Control</button><button className="secondary-button" type="button" onClick={() => navigate('/runtime')}>Open Runtime</button><button className="secondary-button" type="button" onClick={() => navigate('/opportunities')}>Open Opportunities</button></div>}
      />

      <SectionCard eyebrow="Governance controls" title="Run profile governance" description="Evaluate state, classify regime, and emit profile recommendation/application decision.">
        <div className="markets-filters__actions">
          <label className="field-group"><span>Decision mode</span><select className="select-input" value={decisionMode} onChange={(e) => setDecisionMode(e.target.value)}><option value="RECOMMEND_ONLY">RECOMMEND_ONLY</option><option value="APPLY_SAFE">APPLY_SAFE</option><option value="APPLY_FORCED">APPLY_FORCED</option></select></label>
          <button className="primary-button" type="button" disabled={running} onClick={() => void onRun()}>{running ? 'Running…' : 'Run profile governance'}</button>
          <button className="secondary-button" type="button" disabled={applying || !current?.decision || current.decision.is_applied} onClick={() => void onApply()}>{applying ? 'Applying…' : 'Apply current decision'}</button>
          {message ? <span className="muted-text">{message}</span> : null}
        </div>
      </SectionCard>

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Summary" title="Current meta-governance state" description="Regime, decision mode, profile targets, and hard constraints.">
          <div className="dashboard-stat-grid">{cards.map((c) => <article key={c.label} className="dashboard-stat-card"><span>{c.label}</span><strong>{c.badge ? <span className={badgeClass(String(c.value))}>{c.value}</span> : c.value}</strong></article>)}</div>
          {summary?.blocking_constraints?.length ? <p><strong>Blocking constraints:</strong> {summary.blocking_constraints.join(', ')}</p> : <p className="muted-text">No blocking constraints currently active.</p>}
        </SectionCard>

        <SectionCard eyebrow="Current decision" title="Recommendation vs apply state" description="Clear rationale and reason codes for the active profile decision.">
          {!current?.decision ? <p className="muted-text">Run profile governance to evaluate adaptive operating profiles.</p> : (
            <div className="system-metadata-grid">
              <div><strong>Regime:</strong> <span className={badgeClass(current.regime)}>{current.regime}</span></div>
              <div><strong>Decision mode:</strong> <span className={badgeClass(current.decision.decision_mode)}>{current.decision.decision_mode}</span></div>
              <div><strong>Recommendation applied:</strong> {current.decision.is_applied ? 'Yes' : 'No'}</div>
              <div><strong>Reason codes:</strong> {current.decision.reason_codes.join(', ') || 'N/A'}</div>
              <div><strong>Rationale:</strong> {current.decision.rationale}</div>
              <div><strong>Affected modules:</strong> research_agent, signals, opportunity_supervisor, mission_control, portfolio_governor</div>
              <div><strong>Targets:</strong> {current.decision.target_research_profile} / {current.decision.target_signal_profile} / {current.decision.target_opportunity_supervisor_profile} / {current.decision.target_mission_control_profile} / {current.decision.target_portfolio_governor_profile}</div>
            </div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Recent runs" title="Governance audit trail" description="Latest regime decisions and target profiles.">
          {runs.length === 0 ? <p className="muted-text">Run profile governance to evaluate adaptive operating profiles.</p> : (
            <div className="markets-table-wrapper">
              <table className="markets-table">
                <thead><tr><th>ID</th><th>Regime</th><th>Decision mode</th><th>Target profiles</th><th>Summary</th><th>Created</th></tr></thead>
                <tbody>
                  {runs.slice(0, 12).map((run) => (
                    <tr key={run.id}>
                      <td>#{run.id}</td>
                      <td><span className={badgeClass(run.regime)}>{run.regime}</span></td>
                      <td><span className={badgeClass(run.decision?.decision_mode ?? '')}>{run.decision?.decision_mode ?? 'N/A'}</span></td>
                      <td>{run.decision ? `${run.decision.target_research_profile} | ${run.decision.target_signal_profile} | ${run.decision.target_mission_control_profile}` : 'N/A'}</td>
                      <td>{run.summary}</td>
                      <td>{run.started_at}</td>
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
